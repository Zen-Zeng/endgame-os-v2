/**
 * 主布局组件
 */
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import { useUIStore } from '../../stores/useUIStore';

export default function MainLayout() {
  const { sidebarCollapsed } = useUIStore();

  return (
    <div 
      className="app-layout"
      style={{ 
        '--current-sidebar-width': sidebarCollapsed ? '80px' : '280px' 
      } as any}
    >
      <Sidebar />
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}

