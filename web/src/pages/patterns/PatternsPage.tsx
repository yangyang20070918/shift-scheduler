import { useEffect, useState } from 'react'
import { Table, Button, Modal, Form, Input, InputNumber, Select, Tag, Space, Popconfirm, ColorPicker, Upload, Alert, message } from 'antd'
import { PlusOutlined, DownloadOutlined, UploadOutlined } from '@ant-design/icons'
import { listPatterns, createPattern, updatePattern, deletePattern, exportPatternsExcel, previewPatternImport, executePatternImport, type Pattern, type PatternImportPreview } from '../../api/patterns'

const PATTERN_TYPES = [
  { label: '勤務', value: 'work' },
  { label: '休日', value: 'rest' },
  { label: '出張', value: 'travel' },
]

const TIME_OPTIONS = Array.from({ length: 48 }, (_, i) => {
  const h = String(Math.floor(i / 2)).padStart(2, '0')
  const m = i % 2 === 0 ? '00' : '30'
  return { label: `${h}:${m}`, value: `${h}:${m}` }
})

const TYPE_LABELS: Record<string, string> = { work: '勤務', rest: '休日', travel: '出張' }

export default function PatternsPage() {
  const [patterns, setPatterns] = useState<Pattern[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Pattern | null>(null)
  const [selectedType, setSelectedType] = useState('work')
  const [form] = Form.useForm()
  const [importModalOpen, setImportModalOpen] = useState(false)
  const [importPreview, setImportPreview] = useState<PatternImportPreview | null>(null)
  const [importFile, setImportFile] = useState<File | null>(null)
  const [importing, setImporting] = useState(false)

  async function load() {
    setLoading(true)
    try {
      setPatterns(await listPatterns())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  function openCreate() {
    setEditing(null)
    form.resetFields()
    setSelectedType('work')
    setModalOpen(true)
  }

  function openEdit(record: Pattern) {
    setEditing(record)
    setSelectedType(record.type)
    form.setFieldsValue({
      ...record,
      color_code: record.color_code,
    })
    setModalOpen(true)
  }

  async function handleSave() {
    try {
      const values = await form.validateFields()
      const color = typeof values.color_code === 'string' ? values.color_code : values.color_code?.toHexString?.() || '#808080'
      const data = {
        ...values,
        color_code: color,
        is_companion: false,
        start_time: values.type === 'work' ? values.start_time : '00:00',
        end_time: values.type === 'work' ? values.end_time : '00:00',
        work_hours: values.type === 'rest' ? 0 : values.work_hours,
        break_hours: values.type === 'work' ? (values.break_hours ?? 0) : 0,
      }
      if (editing) {
        await updatePattern(editing.id, data)
        message.success('更新しました')
      } else {
        await createPattern(data)
        message.success('パターンを作成しました')
      }
      setModalOpen(false)
      load()
    } catch (e: any) {
      if (e?.errorFields) return
      message.error(e?.response?.data?.detail || e?.message || '保存に失敗しました')
    }
  }

  async function handleDelete(id: string) {
    await deletePattern(id)
    message.success('削除しました')
    load()
  }

  async function handleImportFile(file: File) {
    setImportFile(file)
    try {
      const preview = await previewPatternImport(file)
      setImportPreview(preview)
      setImportModalOpen(true)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'プレビューに失敗しました')
    }
    return false
  }

  async function handleImportExecute() {
    if (!importFile) return
    setImporting(true)
    try {
      const result = await executePatternImport(importFile)
      message.success(`新規 ${result.created} 件、更新 ${result.updated} 件`)
      setImportModalOpen(false)
      setImportFile(null)
      setImportPreview(null)
      load()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'インポートに失敗しました')
    } finally {
      setImporting(false)
    }
  }

  const isWork = selectedType === 'work'
  const isRest = selectedType === 'rest'

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
      render: (t: string) => <Tag>{TYPE_LABELS[t] || t}</Tag>,
    },
    {
      title: '時間帯',
      key: 'time',
      render: (_: any, r: Pattern) => r.type === 'work' ? `${r.start_time} - ${r.end_time}` : '-',
    },
    {
      title: '実労働時間',
      dataIndex: 'work_hours',
      key: 'work_hours',
      render: (v: number, r: Pattern) => r.type === 'rest' ? '-' : v,
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: any, record: Pattern) => (
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
        <h2 style={{ margin: 0 }}>出勤パターン</h2>
        <Space>
          <Button icon={<DownloadOutlined />} onClick={() => exportPatternsExcel()}>
            Excel出力
          </Button>
          <Upload accept=".xlsx,.xls" showUploadList={false} beforeUpload={handleImportFile}>
            <Button icon={<UploadOutlined />}>Excelインポート</Button>
          </Upload>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            パターン追加
          </Button>
        </Space>
      </div>

      <Table dataSource={patterns} columns={columns} rowKey="id" loading={loading} />

      <Modal
        title={editing ? 'パターンを編集' : 'パターン追加'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
      >
        <Form form={form} layout="vertical" initialValues={{ type: 'work', start_time: '09:00', end_time: '17:00', break_hours: 1, work_hours: 7, color_code: '#1677ff' }}>
          <Form.Item name="name" label="名前" rules={[{ required: true }]}>
            <Input placeholder="例: 日勤" />
          </Form.Item>
          <Form.Item name="type" label="タイプ" rules={[{ required: true }]}>
            <Select options={PATTERN_TYPES} onChange={(v) => setSelectedType(v)} />
          </Form.Item>
          {isWork && (
            <div style={{ display: 'flex', gap: 16 }}>
              <Form.Item name="start_time" label="開始時刻" rules={[{ required: true }]} style={{ flex: 1 }}>
                <Select options={TIME_OPTIONS} showSearch />
              </Form.Item>
              <Form.Item name="end_time" label="終了時刻" rules={[{ required: true }]} style={{ flex: 1 }}>
                <Select options={TIME_OPTIONS} showSearch />
              </Form.Item>
            </div>
          )}
          {!isRest && (
            <div style={{ display: 'flex', gap: 16 }}>
              <Form.Item name="work_hours" label="実労働時間" rules={[{ required: true }]} style={{ flex: 1 }}>
                <InputNumber min={0} max={24} step={0.5} style={{ width: '100%' }} />
              </Form.Item>
              {isWork && (
                <Form.Item name="break_hours" label="休憩時間" style={{ flex: 1 }}>
                  <InputNumber min={0} max={4} step={0.5} style={{ width: '100%' }} />
                </Form.Item>
              )}
            </div>
          )}
          <Form.Item name="color_code" label="色">
            <ColorPicker />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="パターンインポート確認"
        open={importModalOpen}
        onOk={handleImportExecute}
        onCancel={() => { setImportModalOpen(false); setImportFile(null); setImportPreview(null) }}
        okText="インポート実行"
        confirmLoading={importing}
        width={600}
      >
        {importPreview && (
          <>
            {importPreview.warnings.length > 0 && (
              <Alert
                type="warning"
                message={importPreview.warnings.map((w, i) => <div key={i}>{w}</div>)}
                style={{ marginBottom: 16 }}
              />
            )}
            <Table
              dataSource={importPreview.patterns.map((p, i) => ({ ...p, key: i }))}
              columns={[
                { title: '名前', dataIndex: 'name', key: 'name' },
                { title: 'タイプ', dataIndex: 'type', key: 'type', render: (t: string) => TYPE_LABELS[t] || t },
                { title: '実労働時間', dataIndex: 'work_hours', key: 'work_hours' },
                {
                  title: 'ステータス',
                  dataIndex: 'status',
                  key: 'status',
                  render: (s: string) => <Tag color={s === 'new' ? 'green' : 'blue'}>{s === 'new' ? '新規' : '更新'}</Tag>,
                },
              ]}
              size="small"
              pagination={false}
            />
          </>
        )}
      </Modal>
    </>
  )
}
