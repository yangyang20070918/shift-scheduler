import { useState } from 'react'
import { Layout, Menu, Button, Typography, Drawer } from 'antd'
import {
  TeamOutlined,
  ScheduleOutlined,
  AppstoreOutlined,
  LogoutOutlined,
  SafetyOutlined,
  ApartmentOutlined,
  MenuOutlined,
} from '@ant-design/icons'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../store/auth'

const { Header, Sider, Content } = Layout

export default function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuth()
  const [drawerOpen, setDrawerOpen] = useState(false)

  const menuItems = [
    { key: '/members', icon: <TeamOutlined />, label: 'メンバー' },
    { key: '/patterns', icon: <AppstoreOutlined />, label: 'パターン' },
    { key: '/groups', icon: <ApartmentOutlined />, label: 'グループ' },
    { key: '/constraints', icon: <SafetyOutlined />, label: '個人制約' },
    { key: '/schedules', icon: <ScheduleOutlined />, label: 'スケジュール' },
  ]

  function handleMenuClick(key: string) {
    navigate(key)
    setDrawerOpen(false)
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        breakpoint="lg"
        collapsedWidth={0}
        trigger={null}
        className="desktop-sider"
        style={{ position: 'fixed', left: 0, top: 0, bottom: 0, zIndex: 10 }}
      >
        <div style={{ padding: '16px', textAlign: 'center' }}>
          <Typography.Title level={4} style={{ color: '#fff', margin: 0 }}>
            シフトスケジューラー
          </Typography.Title>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>

      <Drawer
        placement="left"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={240}
        styles={{ body: { padding: 0, background: '#001529' } }}
        className="mobile-drawer"
      >
        <div style={{ padding: '16px', textAlign: 'center' }}>
          <Typography.Title level={4} style={{ color: '#fff', margin: 0 }}>
            シフトスケジューラー
          </Typography.Title>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => handleMenuClick(key)}
        />
      </Drawer>

      <Layout className="main-layout">
        <Header style={{
          background: '#fff',
          padding: '0 16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 8,
          position: 'sticky',
          top: 0,
          zIndex: 5,
          boxShadow: '0 1px 4px rgba(0,0,0,0.1)',
        }}>
          <Button
            className="mobile-menu-btn"
            icon={<MenuOutlined />}
            type="text"
            onClick={() => setDrawerOpen(true)}
          />
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 'auto' }}>
            <span className="user-info">{user?.name}</span>
            <Button icon={<LogoutOutlined />} onClick={logout} size="small">
              ログアウト
            </Button>
          </div>
        </Header>
        <Content style={{ margin: '16px', padding: '16px', background: '#fff', borderRadius: 8, overflow: 'auto' }}>
          <Outlet />
        </Content>
      </Layout>

      <style>{`
        .desktop-sider { display: block; }
        .mobile-menu-btn { display: none !important; }
        .main-layout { margin-left: 200px; }

        @media (max-width: 991px) {
          .desktop-sider { display: none !important; }
          .mobile-menu-btn { display: inline-flex !important; }
          .main-layout { margin-left: 0 !important; }
        }

        @media (max-width: 576px) {
          .user-info { display: none; }
        }
      `}</style>
    </Layout>
  )
}
