import { useEffect, useState } from 'react'
import { Table, Button, Modal, Form, InputNumber, Select, Space, Popconfirm, message, Card } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { listConstraints, createConstraint, updateConstraint, deleteConstraint, type PersonConstraint } from '../../api/constraints'
import { listMembers, type Member } from '../../api/members'

export default function ConstraintsPage() {
  const [constraints, setConstraints] = useState<PersonConstraint[]>([])
  const [members, setMembers] = useState<Member[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<PersonConstraint | null>(null)
  const [form] = Form.useForm()

  async function load() {
    setLoading(true)
    try {
      const [c, m] = await Promise.all([listConstraints(), listMembers()])
      setConstraints(c)
      setMembers(m)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  function getMemberName(memberId: string) {
    return members.find((m) => m.id === memberId)?.name || memberId
  }

  function openCreate() {
    setEditing(null)
    form.resetFields()
    setModalOpen(true)
  }

  function openEdit(record: PersonConstraint) {
    setEditing(record)
    form.setFieldsValue(record)
    setModalOpen(true)
  }

  async function handleSave() {
    const values = await form.validateFields()
    if (editing) {
      await updateConstraint(editing.id, values)
      message.success('更新しました')
    } else {
      await createConstraint(values)
      message.success('作成しました')
    }
    setModalOpen(false)
    load()
  }

  async function handleDelete(id: string) {
    await deleteConstraint(id)
    message.success('削除しました')
    load()
  }

  const columns = [
    {
      title: 'メンバー',
      dataIndex: 'member_id',
      key: 'member',
      render: (id: string) => getMemberName(id),
    },
    {
      title: '週勤務日数',
      key: 'weekly_days',
      render: (_: any, r: PersonConstraint) =>
        r.weekly_work_days_min != null || r.weekly_work_days_max != null
          ? `${r.weekly_work_days_min ?? '-'} ~ ${r.weekly_work_days_max ?? '-'}`
          : '-',
    },
    {
      title: '期間勤務日数',
      key: 'period_days',
      render: (_: any, r: PersonConstraint) =>
        r.period_work_days_min != null || r.period_work_days_max != null
          ? `${r.period_work_days_min ?? '-'} ~ ${r.period_work_days_max ?? '-'}`
          : '-',
    },
    {
      title: '連続勤務上限',
      dataIndex: 'max_consecutive_work_days',
      key: 'consec_work',
      render: (v: number | null) => v ?? '-',
    },
    {
      title: '連続休息上限',
      dataIndex: 'max_consecutive_rest_days',
      key: 'consec_rest',
      render: (v: number | null) => v ?? '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: any, record: PersonConstraint) => (
        <Space>
          <Button size="small" onClick={() => openEdit(record)}>編集</Button>
          <Popconfirm title="削除しますか？" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger>削除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2 style={{ margin: 0 }}>個人制約</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          制約追加
        </Button>
      </div>

      <Table dataSource={constraints} columns={columns} rowKey="id" loading={loading} />

      <Modal
        title={editing ? '制約を編集' : '制約を追加'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="member_id" label="メンバー" rules={[{ required: true }]}>
            <Select
              placeholder="メンバーを選択"
              options={members.map((m) => ({ label: m.name, value: m.id }))}
            />
          </Form.Item>

          <Card size="small" title="勤務日数" style={{ marginBottom: 16 }}>
            <Space>
              <Form.Item name="weekly_work_days_min" label="週 最小" style={{ marginBottom: 0 }}>
                <InputNumber min={0} max={7} />
              </Form.Item>
              <Form.Item name="weekly_work_days_max" label="週 最大" style={{ marginBottom: 0 }}>
                <InputNumber min={0} max={7} />
              </Form.Item>
              <Form.Item name="period_work_days_min" label="期間 最小" style={{ marginBottom: 0 }}>
                <InputNumber min={0} />
              </Form.Item>
              <Form.Item name="period_work_days_max" label="期間 最大" style={{ marginBottom: 0 }}>
                <InputNumber min={0} />
              </Form.Item>
            </Space>
          </Card>

          <Card size="small" title="勤務時間" style={{ marginBottom: 16 }}>
            <Space>
              <Form.Item name="weekly_work_hours_min" label="週 最小h" style={{ marginBottom: 0 }}>
                <InputNumber min={0} step={0.5} />
              </Form.Item>
              <Form.Item name="weekly_work_hours_max" label="週 最大h" style={{ marginBottom: 0 }}>
                <InputNumber min={0} step={0.5} />
              </Form.Item>
              <Form.Item name="period_work_hours_min" label="期間 最小h" style={{ marginBottom: 0 }}>
                <InputNumber min={0} step={0.5} />
              </Form.Item>
              <Form.Item name="period_work_hours_max" label="期間 最大h" style={{ marginBottom: 0 }}>
                <InputNumber min={0} step={0.5} />
              </Form.Item>
            </Space>
          </Card>

          <Card size="small" title="連続日数">
            <Space>
              <Form.Item name="max_consecutive_work_days" label="連続勤務上限" style={{ marginBottom: 0 }}>
                <InputNumber min={1} max={31} />
              </Form.Item>
              <Form.Item name="max_consecutive_rest_days" label="連続休息上限" style={{ marginBottom: 0 }}>
                <InputNumber min={1} max={31} />
              </Form.Item>
            </Space>
          </Card>
        </Form>
      </Modal>
    </>
  )
}
