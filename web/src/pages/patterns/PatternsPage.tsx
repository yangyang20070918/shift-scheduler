import { useEffect, useState } from 'react'
import { Table, Button, Modal, Form, Input, InputNumber, Select, Tag, Popconfirm, ColorPicker, message } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { listPatterns, createPattern, deletePattern, type Pattern } from '../../api/patterns'

const PATTERN_TYPES = [
  { label: '勤務', value: 'work' },
  { label: '休憩', value: 'rest' },
  { label: '休暇', value: 'leave' },
  { label: '研修', value: 'training' },
  { label: '会議', value: 'meeting' },
  { label: '待機', value: 'oncall' },
]

export default function PatternsPage() {
  const [patterns, setPatterns] = useState<Pattern[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  async function load() {
    setLoading(true)
    try {
      setPatterns(await listPatterns())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function handleCreate() {
    const values = await form.validateFields()
    const color = typeof values.color_code === 'string' ? values.color_code : values.color_code?.toHexString?.() || '#808080'
    await createPattern({ ...values, color_code: color, is_companion: false })
    message.success('パターンを作成しました')
    setModalOpen(false)
    form.resetFields()
    load()
  }

  async function handleDelete(id: string) {
    await deletePattern(id)
    message.success('削除しました')
    load()
  }

  const columns = [
    {
      title: '色',
      dataIndex: 'color_code',
      key: 'color',
      width: 60,
      render: (c: string) => <div style={{ width: 24, height: 24, background: c, borderRadius: 4 }} />,
    },
    { title: '名前', dataIndex: 'name', key: 'name' },
    {
      title: 'タイプ',
      dataIndex: 'type',
      key: 'type',
      render: (t: string) => <Tag>{t}</Tag>,
    },
    { title: '時間帯', key: 'time', render: (_: any, r: Pattern) => `${r.start_time} - ${r.end_time}` },
    { title: '勤務時間', dataIndex: 'work_hours', key: 'work_hours' },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: any, record: Pattern) => (
        <Popconfirm title="削除しますか？" onConfirm={() => handleDelete(record.id)}>
          <Button size="small" danger>削除</Button>
        </Popconfirm>
      ),
    },
  ]

  return (
    <>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2 style={{ margin: 0 }}>シフトパターン</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { form.resetFields(); setModalOpen(true) }}>
          パターン追加
        </Button>
      </div>

      <Table dataSource={patterns} columns={columns} rowKey="id" loading={loading} />

      <Modal title="パターン追加" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)}>
        <Form form={form} layout="vertical" initialValues={{ type: 'work', start_time: '09:00', end_time: '17:00', break_hours: 1, work_hours: 7, color_code: '#1677ff' }}>
          <Form.Item name="name" label="名前" rules={[{ required: true }]}>
            <Input placeholder="例: 日勤" />
          </Form.Item>
          <Form.Item name="type" label="タイプ" rules={[{ required: true }]}>
            <Select options={PATTERN_TYPES} />
          </Form.Item>
          <div style={{ display: 'flex', gap: 16 }}>
            <Form.Item name="start_time" label="開始時刻" rules={[{ required: true }]} style={{ flex: 1 }}>
              <Input placeholder="09:00" />
            </Form.Item>
            <Form.Item name="end_time" label="終了時刻" rules={[{ required: true }]} style={{ flex: 1 }}>
              <Input placeholder="17:00" />
            </Form.Item>
          </div>
          <div style={{ display: 'flex', gap: 16 }}>
            <Form.Item name="work_hours" label="勤務時間" rules={[{ required: true }]} style={{ flex: 1 }}>
              <InputNumber min={0} max={24} step={0.5} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="break_hours" label="休憩時間" style={{ flex: 1 }}>
              <InputNumber min={0} max={4} step={0.5} style={{ width: '100%' }} />
            </Form.Item>
          </div>
          <Form.Item name="color_code" label="色">
            <ColorPicker />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
