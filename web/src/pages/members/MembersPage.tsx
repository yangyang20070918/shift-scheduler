import { useEffect, useState } from 'react'
import { Table, Button, Modal, Form, Input, Select, Space, Popconfirm, Upload, Alert, List, Tag, message } from 'antd'
import { PlusOutlined, DownloadOutlined, UploadOutlined } from '@ant-design/icons'
import { listMembers, createMember, updateMember, deleteMember, type Member } from '../../api/members'
import { listPatterns, type Pattern } from '../../api/patterns'
import { downloadTemplate, previewImport, executeImport, type ImportPreview } from '../../api/imports'

export default function MembersPage() {
  const [members, setMembers] = useState<Member[]>([])
  const [patterns, setPatterns] = useState<Pattern[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Member | null>(null)
  const [importModalOpen, setImportModalOpen] = useState(false)
  const [importPreview, setImportPreview] = useState<ImportPreview | null>(null)
  const [importFile, setImportFile] = useState<File | null>(null)
  const [form] = Form.useForm()

  async function load() {
    setLoading(true)
    try {
      const [m, p] = await Promise.all([listMembers(), listPatterns()])
      setMembers(m)
      setPatterns(p)
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

  function openEdit(record: Member) {
    setEditing(record)
    form.setFieldsValue(record)
    setModalOpen(true)
  }

  async function handleSave() {
    const values = await form.validateFields()
    if (editing) {
      await updateMember(editing.id, values)
      message.success('更新しました')
    } else {
      await createMember(values)
      message.success('作成しました')
    }
    setModalOpen(false)
    load()
  }

  async function handleDelete(id: string) {
    await deleteMember(id)
    message.success('削除しました')
    load()
  }

  async function handleImportPreview(file: File) {
    setImportFile(file)
    try {
      const preview = await previewImport(file)
      setImportPreview(preview)
      setImportModalOpen(true)
    } catch {
      message.error('ファイルの読み込みに失敗しました')
    }
  }

  async function handleImportExecute() {
    if (!importFile) return
    try {
      const result = await executeImport(importFile)
      message.success(`インポート完了: 新規${result.members_created}件、更新${result.members_updated}件`)
      setImportModalOpen(false)
      setImportPreview(null)
      setImportFile(null)
      load()
    } catch {
      message.error('インポートに失敗しました')
    }
  }

  const columns = [
    { title: '名前', dataIndex: 'name', key: 'name' },
    {
      title: '対応可能パターン',
      dataIndex: 'available_pattern_ids',
      key: 'patterns',
      render: (ids: string[]) =>
        ids.map((id) => patterns.find((p) => p.id === id)?.name || id).join(', ') || '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: any, record: Member) => (
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
        <h2 style={{ margin: 0 }}>メンバー</h2>
        <Space>
          <Button icon={<DownloadOutlined />} onClick={() => downloadTemplate()}>
            テンプレート
          </Button>
          <Upload
            accept=".xlsx"
            showUploadList={false}
            beforeUpload={(file) => { handleImportPreview(file); return false }}
          >
            <Button icon={<UploadOutlined />}>Excelインポート</Button>
          </Upload>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            メンバー追加
          </Button>
        </Space>
      </div>

      <Table dataSource={members} columns={columns} rowKey="id" loading={loading} />

      <Modal
        title={editing ? 'メンバーを編集' : 'メンバーを追加'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名前" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="available_pattern_ids" label="対応可能パターン">
            <Select
              mode="multiple"
              placeholder="パターンを選択"
              options={patterns.map((p) => ({ label: p.name, value: p.id }))}
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="インポートプレビュー"
        open={importModalOpen}
        onOk={handleImportExecute}
        onCancel={() => { setImportModalOpen(false); setImportPreview(null); setImportFile(null) }}
        okText="インポート実行"
        cancelText="キャンセル"
        width={600}
      >
        {importPreview && (
          <>
            {importPreview.warnings.length > 0 && (
              <Alert
                type="warning"
                style={{ marginBottom: 16 }}
                message="警告"
                description={
                  <List
                    size="small"
                    dataSource={importPreview.warnings}
                    renderItem={(w) => <List.Item>{w}</List.Item>}
                  />
                }
              />
            )}
            <h4>メンバー（{importPreview.members.length}件）</h4>
            <List
              size="small"
              dataSource={importPreview.members}
              renderItem={(m) => (
                <List.Item>
                  <Tag color={m.status === 'new' ? 'green' : 'blue'}>
                    {m.status === 'new' ? '新規' : '更新'}
                  </Tag>
                  {m.name}
                  {m.pattern_names.length > 0 && (
                    <span style={{ marginLeft: 8, color: '#888' }}>
                      ({m.pattern_names.join(', ')})
                    </span>
                  )}
                </List.Item>
              )}
            />
            {importPreview.constraints.length > 0 && (
              <>
                <h4 style={{ marginTop: 16 }}>個人制約（{importPreview.constraints.length}件）</h4>
                <List
                  size="small"
                  dataSource={importPreview.constraints}
                  renderItem={(c) => <List.Item>{c.member_name}: {JSON.stringify(c)}</List.Item>}
                />
              </>
            )}
          </>
        )}
      </Modal>
    </>
  )
}
