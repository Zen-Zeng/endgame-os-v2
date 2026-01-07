"""
档案库 API 路由
处理文件上传、管理、搜索和预览
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import uuid
import os
import shutil

from ..models.user import User
from .auth import require_user

router = APIRouter()


# ============ 配置 ============

UPLOAD_DIR = Path("uploads")
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

_files_db: dict[str, dict] = {}  # file_id -> ArchiveFile
_folders_db: dict[str, dict] = {}  # folder_id -> ArchiveFolder


# ============ 辅助函数 ============

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

@router.get("/files", response_model=List[ArchiveFile])
async def list_files(
    folder_id: Optional[str] = None,
    file_type: Optional[str] = None,
    tags: Optional[str] = Query(default=None, description="标签，逗号分隔"),
    search: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(require_user)
):
    """
    获取文件列表
    """
    files = [f for f in _files_db.values() if f["user_id"] == user.id]
    
    # 过滤
    if file_type:
        files = [f for f in files if f["file_type"] == file_type]
    
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        files = [f for f in files if any(t in f["tags"] for t in tag_list)]
    
    if search:
        search_lower = search.lower()
        files = [
            f for f in files
            if search_lower in f["original_name"].lower()
            or (f.get("description") and search_lower in f["description"].lower())
        ]
    
    # 排序和分页
    sorted_files = sorted(files, key=lambda x: x["created_at"], reverse=True)
    paginated = sorted_files[offset:offset + limit]
    
    return [ArchiveFile(**f) for f in paginated]


@router.post("/upload", response_model=ArchiveFile)
async def upload_file(
    file: UploadFile = File(...),
    folder_id: Optional[str] = None,
    tags: Optional[str] = None,
    description: Optional[str] = None,
    user: User = Depends(require_user)
):
    """
    上传文件
    """
    _validate_file(file)
    
    # 生成唯一文件名
    file_id = f"file_{uuid.uuid4().hex[:8]}"
    ext = Path(file.filename).suffix
    stored_name = f"{file_id}{ext}"
    
    # 确保上传目录存在
    user_dir = UPLOAD_DIR / user.id
    user_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存文件
    file_path = user_dir / stored_name
    content = await file.read()
    
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件大小超过限制 (100MB)")
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    # 创建记录
    archive_file = ArchiveFile(
        id=file_id,
        user_id=user.id,
        filename=stored_name,
        original_name=file.filename,
        file_type=_get_file_type(file.filename),
        file_size=len(content),
        mime_type=file.content_type,
        tags=[t.strip() for t in tags.split(",")] if tags else [],
        description=description,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    _files_db[file_id] = archive_file.model_dump()
    
    return archive_file


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
    if file_data["user_id"] != user.id:
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

