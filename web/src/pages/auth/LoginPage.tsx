import { useState } from 'react'
import { Card, Form, Input, Button, Typography, message, Tabs } from 'antd'
import { useNavigate } from 'react-router-dom'
import { login, register, getMe } from '../../api/auth'
import { useAuth } from '../../store/auth'

export default function LoginPage() {
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const { setAuth } = useAuth()

  async function handleLogin(values: { email: string; password: string }) {
    setLoading(true)
    try {
      const token = await login(values.email, values.password)
      localStorage.setItem('token', token)
      const user = await getMe()
      setAuth(token, user)
      navigate('/schedules')
    } catch {
      message.error('ログインに失敗しました。メールアドレスとパスワードを確認してください。')
    } finally {
      setLoading(false)
    }
  }

  async function handleRegister(values: { email: string; password: string; name: string; tenant_name: string }) {
    setLoading(true)
    try {
      await register(values)
      const token = await login(values.email, values.password)
      localStorage.setItem('token', token)
      const user = await getMe()
      setAuth(token, user)
      message.success('登録が完了しました！')
      navigate('/schedules')
    } catch (err: any) {
      const detail = err.response?.data?.detail || '登録に失敗しました。'
      message.error(detail)
    } finally {
      setLoading(false)
    }
  }

  const items = [
    {
      key: 'login',
      label: 'ログイン',
      children: (
        <Form layout="vertical" onFinish={handleLogin}>
          <Form.Item name="email" label="メールアドレス" rules={[{ required: true, type: 'email' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="password" label="パスワード" rules={[{ required: true }]}>
            <Input.Password />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={loading} block>
            ログイン
          </Button>
        </Form>
      ),
    },
    {
      key: 'register',
      label: '新規登録',
      children: (
        <Form layout="vertical" onFinish={handleRegister}>
          <Form.Item name="tenant_name" label="組織名" rules={[{ required: true }]}>
            <Input placeholder="会社名を入力" />
          </Form.Item>
          <Form.Item name="name" label="氏名" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="email" label="メールアドレス" rules={[{ required: true, type: 'email' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="password" label="パスワード" rules={[{ required: true, min: 4 }]}>
            <Input.Password />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={loading} block>
            登録
          </Button>
        </Form>
      ),
    },
  ]

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f0f2f5' }}>
      <Card style={{ width: 400 }}>
        <Typography.Title level={3} style={{ textAlign: 'center' }}>
          シフトスケジューラー
        </Typography.Title>
        <Tabs items={items} centered />
      </Card>
    </div>
  )
}
