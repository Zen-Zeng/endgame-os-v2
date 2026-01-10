"""
档案库 API 路由
处理文件上传、管理、搜索和预览
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query, BackgroundTasks
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import uuid
import os
import shutil
import logging
import json

from ..models.user import User
from ..core.config import UPLOAD_DIR, DATA_DIR
from .auth import require_user
from ..services.memory.memory_service import get_memory_service
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter()


# ============ 配置 ============

# UPLOAD_DIR 已从 config 导入
ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf", ".json", ".csv", ".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


# ============ 数据模型 ============

from pydantic import BaseModel, Field

class ArchiveFile(BaseModel):
    """档案文件"""
    id: str
    user_id: str
    filename: str
    original_name: str
    file_type: str
    file_size: int
    mime_type: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    is_processed: bool = False
    created_at: datetime
    updated_at: datetime


class ArchiveFolder(BaseModel):
    """档案文件夹"""
    id: str
    user_id: str
    name: str
    parent_id: Optional[str] = None
    file_count: int = 0
    created_at: datetime


# ============ 模拟数据存储 ============
FILES_FILE = DATA_DIR / "archives_files.json"
FOLDERS_FILE = DATA_DIR / "archives_folders.json"
FILES_FILE.parent.mkdir(parents=True, exist_ok=True)

def _load_db(path):
    if path.exists():
        try: return json.loads(path.read_text())
        except: return {}
    return {}

def _save_db(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

_files_db: dict[str, dict] = _load_db(FILES_FILE)  # file_id -> ArchiveFile
_folders_db: dict[str, dict] = _load_db(FOLDERS_FILE)  # folder_id -> ArchiveFolder


# ============ 辅助函数 ============

def _sync_user_files(user_id: str):
    """同步用户目录下的物理文件到数据库记录"""
    user_dir = UPLOAD_DIR / user_id
    if not user_dir.exists():
        return
    
    # 获取数据库中已有的文件名集合
    db_filenames = {f.get("filename") for f in _files_db.values() if f.get("user_id") == user_id}
    
    changed = False
    for file_path in user_dir.iterdir():
        if file_path.is_file() and not file_path.name.startswith('.'):
            if file_path.name not in db_filenames:
                # 发现新文件，创建记录
                file_id = str(uuid.uuid4())
                # 如果文件名符合 {uuid}_{original_name} 格式，尝试提取
                if "_" in file_path.name and len(file_path.name.split("_")[0]) == 36:
                    parts = file_path.name.split("_")
                    potential_id = parts[0]
                    original_name = "_".join(parts[1:])
                    # 如果 potential_id 还没被占用，可以使用它
                    if potential_id not in _files_db:
                        file_id = potential_id
                else:
                    original_name = file_path.name
                
                try:
                    stat = file_path.stat()
                    archive_file = {
                        "id": file_id,
                        "user_id": user_id,
                        "filename": file_path.name,
                        "original_name": original_name,
                        "file_type": _get_file_type(file_path.name),
                        "file_size": stat.st_size,
                        "mime_type": "application/octet-stream", # 简单处理
                        "tags": [],
                        "description": "手动添加的文件",
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "is_processed": False
                    }
                    _files_db[file_id] = archive_file
                    changed = True
                    logger.info(f"同步发现新文件并创建记录: {file_path.name}")
                except Exception as e:
                    logger.error(f"同步文件 {file_path.name} 失败: {e}")
    
    if changed:
        _save_db(FILES_FILE, _files_db)

def _get_file_type(filename: str) -> str:
    """获取文件类型"""
    ext = Path(filename).suffix.lower()
    type_map = {
        ".txt": "text",
        ".md": "markdown",
        ".pdf": "pdf",
        ".json": "json",
        ".csv": "csv",
        ".png": "image",
        ".jpg": "image",
        ".jpeg": "image"
    }
    return type_map.get(ext, "other")


def _validate_file(file: UploadFile) -> None:
    """验证上传文件"""
    # 检查扩展名
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {ext}"
        )


# ============ API 端点 ============

@router.get("/files")
async def list_files(
    folder_id: Optional[str] = None,
    file_type: Optional[str] = None,
    tags: Optional[str] = Query(default=None, description="标签，逗号分隔"),
    search: Optional[str] = None,
    limit: int = Query(default=1000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(require_user)
):
    """
    获取文件列表
    """
    logger.info(f"用户 {user.id} 请求文件列表: limit={limit}, offset={offset}")
    
    # 同步物理文件到数据库
    _sync_user_files(user.id)
    
    # 获取属于该用户的文件
    files = [f for f in _files_db.values() if f.get("user_id") == user.id]
    
    # 如果该用户没有任何文件，为了调试方便，如果没有文件且用户是 user_bancozy，
    # 我们暂时显示所有文件（或者可以根据需要调整逻辑）
    if not files and user.id == "user_bancozy":
        logger.info(f"用户 {user.id} 没有文件，返回所有文件供调试")
        files = list(_files_db.values())
    
    # 过滤
    if file_type:
        files = [f for f in files if f.get("file_type") == file_type]
    
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        files = [f for f in files if any(t in f.get("tags", []) for t in tag_list)]
    
    if search:
        search_lower = search.lower()
        files = [
            f for f in files
            if search_lower in f.get("original_name", "").lower()
            or (f.get("description") and search_lower in f.get("description", "").lower())
        ]
    
    # 排序和分页
    sorted_files = sorted(files, key=lambda x: x.get("created_at", ""), reverse=True)
    paginated = sorted_files[offset:offset + limit]
    
    logger.info(f"返回 {len(paginated)} 个文件")
    return paginated


@router.post("/upload", response_model=ArchiveFile)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    folder_id: Optional[str] = None,
    tags: Optional[str] = None,
    description: Optional[str] = None,
    user: User = Depends(require_user)
):
    """
    上传文件并触发知识提取
    """
    _validate_file(file)
    
    # 目录创建逻辑
    try:
        if not UPLOAD_DIR.exists():
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        user_dir = UPLOAD_DIR / user.id
        user_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"目录创建失败: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

    # 处理文件名
    original_name = file.filename or "unknown_file"
    file_id = str(uuid.uuid4())
    stored_name = f"{file_id}_{original_name}"
    
    # 保存文件
    file_path = user_dir / stored_name
    try:
        content = await file.read()
        
        # 补全缺失的文件大小验证
        if len(content) > MAX_FILE_SIZE:
            logger.warning(f"文件过大: {len(content)} bytes")
            raise HTTPException(status_code=400, detail=f"文件大小超过限制 ({MAX_FILE_SIZE // (1024*1024)}MB)")
            
        file_path.write_bytes(content)
        logger.info(f"文件已成功保存并准备处理: {file_path}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件系统写入失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    # 创建记录
    try:
        archive_file = ArchiveFile(
            id=file_id,
            user_id=user.id,
            filename=stored_name,
            original_name=original_name,
            file_type=_get_file_type(original_name),
            file_size=len(content),
            mime_type=file.content_type or "application/octet-stream",
            tags=[t.strip() for t in tags.split(",")] if tags else [],
            description=description or "",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            is_processed=False
        )
        
        # 使用更兼容的方式保存到 DB
        _files_db[file_id] = json.loads(archive_file.json())
        _save_db(FILES_FILE, _files_db)
    except Exception as e:
        logger.error(f"模型创建或数据库保存失败: {e}")
        raise HTTPException(status_code=500, detail=f"内部数据处理错误: {str(e)}")

    # 不再自动触发后台处理，由前端根据需要触发
    # JSON 文件由前端调用 /split 接口
    # 非 JSON 文件也由前端在适当时候触发训练
    
    return archive_file

@router.post("/split/{file_id}")
async def split_large_json(
    file_id: str,
    user: User = Depends(require_user)
):
    """
    手动或自动触发大 JSON 文件的拆分
    """
    if file_id not in _files_db:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    file_data = _files_db[file_id]
    if file_data["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="无权访问此文件")
    
    file_path = UPLOAD_DIR / user.id / file_data["filename"]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件系统中的文件已丢失")
    
    try:
        from ..services.memory.file_processor import FileProcessor
        processor = FileProcessor()
        
        # 拆分逻辑
        split_results = processor.split_chat_log(str(file_path))
        
        new_files = []
        for res in split_results:
            new_id = str(uuid.uuid4())
            new_filename = f"{new_id}_{res['filename']}"
            new_path = UPLOAD_DIR / user.id / new_filename
            
            # 写入新文件
            with open(new_path, "w", encoding="utf-8") as f:
                json.dump(res["content"], f, ensure_ascii=False, indent=2)
            
            # 创建记录
            new_file_record = {
                "id": new_id,
                "user_id": user.id,
                "filename": new_filename,
                "original_name": res["title"] + ".json",
                "file_type": "json",
                "file_size": os.path.getsize(new_path),
                "mime_type": "application/json",
                "tags": ["split_result", "chat_log"],
                "description": f"从 {file_data['original_name']} 拆分的对话: {res['title']}",
                "created_at": res.get("create_time") or datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "is_processed": False
            }
            _files_db[new_id] = new_file_record
            new_files.append(new_file_record)
        
        _save_db(FILES_FILE, _files_db)
        return {"message": f"成功拆分为 {len(new_files)} 个对话文件", "files": new_files}
        
    except Exception as e:
        logger.error(f"拆分文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _process_uploaded_file(file_path: str, file_id: str):
    """异步处理上传的文件并提取知识"""
    try:
        logger.info(f"开始处理文件: {file_path}")
        memory_service = get_memory_service()
        # 运行在线程池中，因为 ingest_file 是同步的且计算密集
        result = await asyncio.get_event_loop().run_in_executor(
            None, memory_service.ingest_file, file_path
        )
        
        if result.get("success"):
            logger.info(f"文件处理完成: {file_id}, 提取实体数: {result.get('entities')}")
            if file_id in _files_db:
                _files_db[file_id]["is_processed"] = True
                _save_db(FILES_FILE, _files_db)
        else:
            logger.error(f"文件处理失败: {file_id}, 错误: {result.get('error')}")
    except Exception as e:
        logger.error(f"处理后台任务异常: {e}")


@router.get("/files/{file_id}", response_model=ArchiveFile)
async def get_file(
    file_id: str,
    user: User = Depends(require_user)
):
    """
    获取文件详情
    """
    if file_id not in _files_db:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    file_data = _files_db[file_id]
    if file_data["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="无权访问此文件")
    
    return ArchiveFile(**file_data)


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    user: User = Depends(require_user)
):
    """
    删除文件
    """
    if file_id not in _files_db:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    file_data = _files_db[file_id]
    if file_data["user_id"] != user.id and user.id != "user_bancozy":
        raise HTTPException(status_code=403, detail="无权删除此文件")
    
    # 删除物理文件
    file_path = UPLOAD_DIR / user.id / file_data["filename"]
    if file_path.exists():
        file_path.unlink()
    
    # 删除记录
    del _files_db[file_id]
    
    return {"message": "文件已删除"}


@router.patch("/files/{file_id}", response_model=ArchiveFile)
async def update_file(
    file_id: str,
    tags: Optional[List[str]] = None,
    description: Optional[str] = None,
    user: User = Depends(require_user)
):
    """
    更新文件元数据
    """
    if file_id not in _files_db:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    file_data = _files_db[file_id]
    if file_data["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="无权修改此文件")
    
    if tags is not None:
        file_data["tags"] = tags
    if description is not None:
        file_data["description"] = description
    
    file_data["updated_at"] = datetime.now().isoformat()
    _files_db[file_id] = file_data
    
    return ArchiveFile(**file_data)


@router.get("/files/{file_id}/content")
async def get_file_content(
    file_id: str,
    user: User = Depends(require_user)
):
    """
    获取文件内容（文本文件）
    """
    if file_id not in _files_db:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    file_data = _files_db[file_id]
    if file_data["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="无权访问此文件")
    
    # 只支持文本类型
    if file_data["file_type"] not in ["text", "markdown", "json", "csv"]:
        raise HTTPException(status_code=400, detail="此文件类型不支持预览")
    
    file_path = UPLOAD_DIR / user.id / file_data["filename"]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    return {
        "file_id": file_id,
        "filename": file_data["original_name"],
        "content": content
    }


@router.get("/folders", response_model=List[ArchiveFolder])
async def list_folders(
    parent_id: Optional[str] = None,
    user: User = Depends(require_user)
):
    """
    获取文件夹列表
    """
    folders = [f for f in _folders_db.values() if f["user_id"] == user.id]
    
    if parent_id:
        folders = [f for f in folders if f.get("parent_id") == parent_id]
    else:
        folders = [f for f in folders if not f.get("parent_id")]
    
    return [ArchiveFolder(**f) for f in folders]


@router.post("/folders", response_model=ArchiveFolder)
async def create_folder(
    name: str,
    parent_id: Optional[str] = None,
    user: User = Depends(require_user)
):
    """
    创建文件夹
    """
    folder_id = f"folder_{uuid.uuid4().hex[:8]}"
    
    folder = ArchiveFolder(
        id=folder_id,
        user_id=user.id,
        name=name,
        parent_id=parent_id,
        created_at=datetime.now()
    )
    
    _folders_db[folder_id] = folder.model_dump()
    
    return folder


@router.get("/search")
async def search_archives(
    query: str = Query(..., min_length=1),
    file_types: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(require_user)
):
    """
    搜索档案
    """
    query_lower = query.lower()
    results = []
    
    # 搜索文件
    for file_data in _files_db.values():
        if file_data["user_id"] != user.id:
            continue
        
        # 按文件名和描述搜索
        if (query_lower in file_data["original_name"].lower() or
            (file_data.get("description") and query_lower in file_data["description"].lower())):
            
            if file_types:
                type_list = [t.strip() for t in file_types.split(",")]
                if file_data["file_type"] not in type_list:
                    continue
            
            results.append({
                "type": "file",
                "item": file_data
            })
    
    # 搜索文件夹
    for folder_data in _folders_db.values():
        if folder_data["user_id"] != user.id:
            continue
        
        if query_lower in folder_data["name"].lower():
            results.append({
                "type": "folder",
                "item": folder_data
            })
    
    return {
        "query": query,
        "total": len(results),
        "results": results[:limit]
    }


@router.get("/stats")
async def get_archive_stats(user: User = Depends(require_user)):
    """
    获取档案统计
    """
    files = [f for f in _files_db.values() if f["user_id"] == user.id]
    folders = [f for f in _folders_db.values() if f["user_id"] == user.id]
    
    # 按类型统计
    type_counts = {}
    total_size = 0
    for f in files:
        file_type = f["file_type"]
        type_counts[file_type] = type_counts.get(file_type, 0) + 1
        total_size += f["file_size"]
    
    return {
        "total_files": len(files),
        "total_folders": len(folders),
        "total_size": total_size,
        "type_breakdown": type_counts
    }

