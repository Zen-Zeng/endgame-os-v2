import BicameralLayout from '../components/layout/BicameralLayout';
import ChatPage from './ChatPage';
import ScreenView from '../components/screen/ScreenView';

/**
 * 双室心智主页面 (Bicameral Mind Page)
 * 整合 “一脑 (ChatPage)” 与 “一屏 (ScreenView)”
 */
export default function BicameralPage() {
  return (
    <BicameralLayout
      brainView={<ChatPage />}
      screenView={<ScreenView />}
    />
  );
}
