import { useEffect, useState } from 'react'
import { Button, Card, Table, Modal, Form, Input, Select, Space, Popconfirm, Tag, message } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { listGroups, createGroup, updateGroup, deleteGroup, type Group } from '../../api/groups'
import { listMembers, type Member } from '../../api/members'

export default function GroupsPage() {
  const [groups, setGroups] = useState<Group[]>([])
  const [members, setMembers] = useState<Member[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Group | null>(null)
  const [form] = Form.useForm()

  async function load() {
    setLoading(true)
    try {
      const [g, m] = await Promise.all([listGroups(), listMembers()])
      setGroups(g)
      setMembers(m)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  function openCreate() {
    setEditing(null)
    form.resetFields()
    setModalOpen(true)
  }

  function openEdit(group: Group) {
    setEditing(group)
    form.setFieldsValue({ name: group.name, member_ids: group.member_ids })
    setModalOpen(true)
  }

  async function handleSubmit() {
    const values = await form.validateFields()
    if (editing) {
      await updateGroup(editing.id, values)
      message.success('グループを更新しました')
    } else {
      await createGroup(values)
      message.success('グループを作成しました')
    }
    setModalOpen(false)
    load()
  }

  async function handleDelete(id: string) {
    await deleteGroup(id)
    message.success('削除しました')
    load()
  }

  const memberMap = Object.fromEntries(members.map((m) => [m.id, m.name]))

  const columns = [
    { title: 'グループ名', dataIndex: 'name', key: 'name' },
    {
      title: 'メンバー',
      dataIndex: 'member_ids',
      key: 'members',
      render: (ids: string[]) => (
        <Space wrap>
          {ids.map((id) => <Tag key={id}>{memberMap[id] || id}</Tag>)}
          {ids.length === 0 && <span style={{ color: '#999' }}>なし</span>}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: any, record: Group) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)} />
          <Popconfirm title="削除しますか？" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <Card
      title="グループ管理"
      extra={<Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新規作成</Button>}
    >
      <Table dataSource={groups} columns={columns} rowKey="id" loading={loading} pagination={false} />

      <Modal
        title={editing ? 'グループを編集' : 'グループを追加'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="保存"
        cancelText="キャンセル"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="グループ名" rules={[{ required: true, message: 'グループ名を入力してください' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="member_ids" label="メンバー" initialValue={[]}>
            <Select
              mode="multiple"
              placeholder="メンバーを選択"
              options={members.map((m) => ({ label: m.name, value: m.id }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}
