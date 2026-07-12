import { useEffect, useState } from 'react'
import { Table, Button, Modal, Form, Input, InputNumber, DatePicker, Tag, Space, message } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import { listSchedules, createSchedule, type Schedule } from '../../api/schedules'

const STATUS_COLORS: Record<string, string> = {
  draft: 'default',
  running: 'processing',
  completed: 'success',
  failed: 'error',
}

export default function SchedulesPage() {
  const [schedules, setSchedules] = useState<Schedule[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()
  const navigate = useNavigate()

  async function load() {
    setLoading(true)
    try {
      setSchedules(await listSchedules())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function handleCreate() {
    const values = await form.validateFields()
    await createSchedule({
      name: values.name,
      start_date: values.start_date.format('YYYY-MM-DD'),
      num_days: values.num_days,
    })
    message.success('スケジュールを作成しました')
    setModalOpen(false)
    form.resetFields()
    load()
  }


  const columns = [
    { title: '名前', dataIndex: 'name', key: 'name' },
    { title: '開始日', dataIndex: 'start_date', key: 'start_date' },
    { title: '日数', dataIndex: 'num_days', key: 'num_days', width: 80 },
    {
      title: 'ステータス',
      dataIndex: 'status',
      key: 'status',
      render: (s: string) => <Tag color={STATUS_COLORS[s]}>{s}</Tag>,
    },
    {
      title: '健全スコア',
      dataIndex: 'health_score',
      key: 'health_score',
      render: (v: number | null) => v != null ? `${v.toFixed(1)}` : '-',
    },
    {
      title: '求解時間',
      dataIndex: 'solve_time_seconds',
      key: 'solve_time',
      render: (v: number | null) => v != null ? `${v.toFixed(1)}s` : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: any, record: Schedule) => (
        <Space>
          <Button size="small" type="primary" onClick={() => navigate(`/schedules/${record.id}`)}>
            {record.status === 'completed' ? '詳細' : '設定'}
          </Button>
          {record.status === 'running' && <Tag color="processing">実行中...</Tag>}
        </Space>
      ),
    },
  ]

  return (
    <>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2 style={{ margin: 0 }}>スケジュール</h2>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load}>更新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { form.resetFields(); setModalOpen(true) }}>
            新規作成
          </Button>
        </Space>
      </div>

      <Table dataSource={schedules} columns={columns} rowKey="id" loading={loading} />

      <Modal title="新規スケジュール" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)}>
        <Form form={form} layout="vertical" initialValues={{ num_days: 31 }}>
          <Form.Item name="name" label="名前" rules={[{ required: true }]}>
            <Input placeholder="例: 2026年7月" />
          </Form.Item>
          <Form.Item name="start_date" label="開始日" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="num_days" label="日数" rules={[{ required: true }]}>
            <InputNumber min={1} max={62} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
