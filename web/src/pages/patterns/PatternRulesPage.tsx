import { useEffect, useState } from 'react'
import { Card, Button, Table, Select, Space, Popconfirm, Checkbox, Modal, Form, Tag, message, Typography } from 'antd'
import { PlusOutlined, DeleteOutlined, ArrowRightOutlined } from '@ant-design/icons'
import { listPatterns, type Pattern } from '../../api/patterns'
import {
  listForbiddenTransitions, createForbiddenTransition, deleteForbiddenTransition,
  listPatternChains, createPatternChain, updatePatternChain, deletePatternChain,
  type ForbiddenTransition, type PatternChain, type ChainNode,
} from '../../api/pattern-rules'

export default function PatternRulesPage() {
  const [patterns, setPatterns] = useState<Pattern[]>([])
  const [forbidden, setForbidden] = useState<ForbiddenTransition[]>([])
  const [chains, setChains] = useState<PatternChain[]>([])
  const [loading, setLoading] = useState(false)
  const [chainModalOpen, setChainModalOpen] = useState(false)
  const [editingChain, setEditingChain] = useState<PatternChain | null>(null)
  const [chainForm] = Form.useForm()
  const [chainNodes, setChainNodes] = useState<ChainNode[]>([])

  const workPatterns = patterns.filter((p) => p.type === 'work')

  async function load() {
    setLoading(true)
    try {
      const [p, ft, ch] = await Promise.all([
        listPatterns(),
        listForbiddenTransitions(),
        listPatternChains(),
      ])
      setPatterns(p)
      setForbidden(ft)
      setChains(ch)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  function getPatternName(id: string) {
    return patterns.find((p) => p.id === id)?.name || id
  }

  function isForbidden(fromId: string, toId: string): string | null {
    const ft = forbidden.find((f) => f.from_pattern_id === fromId && f.to_pattern_id === toId)
    return ft ? ft.id : null
  }

  async function toggleForbidden(fromId: string, toId: string) {
    const existingId = isForbidden(fromId, toId)
    try {
      if (existingId) {
        await deleteForbiddenTransition(existingId)
        message.success('禁止解除しました')
      } else {
        await createForbiddenTransition({ from_pattern_id: fromId, to_pattern_id: toId })
        message.success('禁止設定しました')
      }
      load()
    } catch {
      message.error('操作に失敗しました')
    }
  }

  function openCreateChain() {
    setEditingChain(null)
    chainForm.resetFields()
    setChainNodes([{ day_offset: 1, candidates: [], is_rest: true }])
    setChainModalOpen(true)
  }

  function openEditChain(chain: PatternChain) {
    setEditingChain(chain)
    chainForm.setFieldsValue({ name: chain.name, trigger_pattern_id: chain.trigger_pattern_id })
    setChainNodes(chain.nodes.length > 0 ? chain.nodes : [{ day_offset: 1, candidates: [], is_rest: true }])
    setChainModalOpen(true)
  }

  function addChainNode() {
    setChainNodes([...chainNodes, { day_offset: chainNodes.length + 1, candidates: [], is_rest: true }])
  }

  function removeChainNode(idx: number) {
    const updated = chainNodes.filter((_, i) => i !== idx).map((n, i) => ({ ...n, day_offset: i + 1 }))
    setChainNodes(updated)
  }

  function updateNode(idx: number, field: keyof ChainNode, value: any) {
    const updated = [...chainNodes]
    if (field === 'is_rest') {
      updated[idx] = { ...updated[idx], is_rest: value, candidates: value ? [] : updated[idx].candidates }
    } else {
      updated[idx] = { ...updated[idx], [field]: value }
    }
    setChainNodes(updated)
  }

  async function handleSaveChain() {
    try {
      const values = await chainForm.validateFields()
      const data = {
        name: values.name || '',
        trigger_pattern_id: values.trigger_pattern_id,
        nodes: chainNodes,
      }
      if (editingChain) {
        await updatePatternChain(editingChain.id, data)
        message.success('更新しました')
      } else {
        await createPatternChain(data)
        message.success('作成しました')
      }
      setChainModalOpen(false)
      load()
    } catch (e: any) {
      if (e?.errorFields) return
      message.error(e?.response?.data?.detail || '保存に失敗しました')
    }
  }

  async function handleDeleteChain(id: string) {
    await deletePatternChain(id)
    message.success('削除しました')
    load()
  }

  const matrixColumns = [
    {
      title: '前日 ＼ 翌日',
      dataIndex: 'name',
      key: 'name',
      fixed: 'left' as const,
      width: 120,
      render: (name: string, record: Pattern) => (
        <span style={{ fontWeight: 500 }}>
          <span style={{ display: 'inline-block', width: 12, height: 12, background: record.color_code, borderRadius: 2, marginRight: 6, verticalAlign: 'middle' }} />
          {name}
        </span>
      ),
    },
    ...workPatterns.map((toP) => ({
      title: <span style={{ fontSize: 12 }}>{toP.name}</span>,
      key: toP.id,
      width: 70,
      align: 'center' as const,
      render: (_: any, fromP: Pattern) => (
        <Checkbox
          checked={!!isForbidden(fromP.id, toP.id)}
          onChange={() => toggleForbidden(fromP.id, toP.id)}
        />
      ),
    })),
  ]

  const chainColumns = [
    { title: '名前', dataIndex: 'name', key: 'name', render: (v: string) => v || '-' },
    {
      title: 'トリガー',
      dataIndex: 'trigger_pattern_id',
      key: 'trigger',
      render: (id: string) => <Tag color="blue">{getPatternName(id)}</Tag>,
    },
    {
      title: '連鎖',
      key: 'sequence',
      render: (_: any, record: PatternChain) => (
        <Space size={4}>
          <Tag color="blue">{getPatternName(record.trigger_pattern_id)}</Tag>
          {record.nodes.map((n, i) => (
            <span key={i}>
              <ArrowRightOutlined style={{ margin: '0 2px', color: '#999' }} />
              <Tag color={n.is_rest ? 'green' : 'orange'}>
                {n.is_rest ? '休日' : n.candidates.map((c) => getPatternName(c)).join('/') || '?'}
              </Tag>
            </span>
          ))}
        </Space>
      ),
    },
    {
      title: '日数',
      dataIndex: 'total_length',
      key: 'length',
      width: 60,
      render: (v: number) => `${v}日`,
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: any, record: PatternChain) => (
        <Space>
          <Button size="small" onClick={() => openEditChain(record)}>編集</Button>
          <Popconfirm title="削除しますか？" onConfirm={() => handleDeleteChain(record.id)}>
            <Button size="small" danger>削除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <>
      <h2>勤務ルール</h2>

      <Card
        title="連続勤務禁止（P1-A）"
        style={{ marginBottom: 16 }}
        extra={<Typography.Text type="secondary">チェック = 禁止</Typography.Text>}
      >
        <Typography.Paragraph type="secondary" style={{ marginBottom: 12 }}>
          前日のパターンの翌日に禁止するパターンを設定します。チェックが入っている組み合わせは連続で割り当てされません。
        </Typography.Paragraph>
        {workPatterns.length > 0 ? (
          <div style={{ overflowX: 'auto' }}>
            <Table
              dataSource={workPatterns}
              columns={matrixColumns}
              rowKey="id"
              loading={loading}
              size="small"
              pagination={false}
              bordered
            />
          </div>
        ) : (
          <Typography.Text type="secondary">勤務パターンを先に登録してください</Typography.Text>
        )}
      </Card>

      <Card
        title="パターンチェーン（P1-B）"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreateChain} disabled={workPatterns.length === 0}>
            チェーン追加
          </Button>
        }
      >
        <Typography.Paragraph type="secondary" style={{ marginBottom: 12 }}>
          特定パターンの出勤後、翌日以降に続くパターン（明け休み等）を定義します。
        </Typography.Paragraph>
        <Table dataSource={chains} columns={chainColumns} rowKey="id" loading={loading} size="small" pagination={false} />
      </Card>

      <Modal
        title={editingChain ? 'チェーンを編集' : 'チェーン追加'}
        open={chainModalOpen}
        onOk={handleSaveChain}
        onCancel={() => setChainModalOpen(false)}
        width={600}
      >
        <Form form={chainForm} layout="vertical">
          <Form.Item name="name" label="名前（任意）">
            <Select
              mode="tags"
              maxCount={1}
              style={{ width: '100%' }}
              placeholder="例: 夜勤連鎖"
              onChange={(vals) => chainForm.setFieldValue('name', vals[0] || '')}
            />
          </Form.Item>
          <Form.Item name="trigger_pattern_id" label="トリガーパターン" rules={[{ required: true }]}>
            <Select
              placeholder="選択"
              options={workPatterns.map((p) => ({ label: p.name, value: p.id }))}
            />
          </Form.Item>
        </Form>

        <Typography.Text strong>後続シーケンス</Typography.Text>
        <div style={{ marginTop: 8 }}>
          {chainNodes.map((node, idx) => (
            <div key={idx} style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'center' }}>
              <Tag>{idx + 1}日目</Tag>
              <Select
                value={node.is_rest ? 'rest' : 'pattern'}
                onChange={(v) => updateNode(idx, 'is_rest', v === 'rest')}
                style={{ width: 100 }}
                options={[
                  { label: '休日', value: 'rest' },
                  { label: 'パターン', value: 'pattern' },
                ]}
              />
              {!node.is_rest && (
                <Select
                  mode="multiple"
                  value={node.candidates}
                  onChange={(v) => updateNode(idx, 'candidates', v)}
                  style={{ flex: 1 }}
                  placeholder="パターンを選択"
                  options={workPatterns.map((p) => ({ label: p.name, value: p.id }))}
                />
              )}
              {chainNodes.length > 1 && (
                <Button size="small" danger icon={<DeleteOutlined />} onClick={() => removeChainNode(idx)} />
              )}
            </div>
          ))}
          <Button type="dashed" onClick={addChainNode} icon={<PlusOutlined />} style={{ width: '100%' }}>
            ノード追加
          </Button>
        </div>
      </Modal>
    </>
  )
}
