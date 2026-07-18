import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Button, InputNumber, Form, Table, Select, Space, Tag, message, Popconfirm, DatePicker, Spin, Row, Col, Statistic, Progress, Modal, Typography, Badge } from 'antd'
import { PlayCircleOutlined, ArrowLeftOutlined, DeleteOutlined, LoadingOutlined, ThunderboltOutlined, SendOutlined, LockOutlined, CopyOutlined, LinkOutlined } from '@ant-design/icons'
import { getScheduleResult, generateSchedule, compareScenarios, updateSchedule, type ScheduleResult, type ScenarioSummary } from '../../api/schedules'
import { listDemands, batchSetDemands, batchSetDemandsByWeekday, clearDemands, listPatternDemands, batchSetPatternDemand, batchSetPatternDemandByWeekday, clearPatternDemands, updateDemand, updatePatternDemand, type DailyDemand, type PatternDemand } from '../../api/demands'
import { listFixedAssignments, createFixedAssignment, updateFixedAssignment, deleteFixedAssignment, type FixedAssignment } from '../../api/fixed-assignments'
import { listMembers, type Member } from '../../api/members'
import { listPatterns, type Pattern } from '../../api/patterns'
import { listGroups, listGroupDemands, updateGroupDemand, deleteGroupDemand, batchSetGroupDemand, batchSetGroupDemandByWeekday, clearGroupDemands, type Group, type GroupDemand } from '../../api/groups'
import { listRestRequests, openRestRequests, closeRestRequests, getMemberToken, type RestDayRequest } from '../../api/rest-requests'

export default function ScheduleDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [schedule, setSchedule] = useState<ScheduleResult | null>(null)
  const [demands, setDemands] = useState<DailyDemand[]>([])
  const [fixedAssignments, setFixedAssignments] = useState<FixedAssignment[]>([])
  const [members, setMembers] = useState<Member[]>([])
  const [patterns, setPatterns] = useState<Pattern[]>([])
  const [groups, setGroups] = useState<Group[]>([])
  const [groupDemands, setGroupDemands] = useState<GroupDemand[]>([])
  const [patternDemands, setPatternDemands] = useState<PatternDemand[]>([])
  const [loading, setLoading] = useState(true)
  const [comparing, setComparing] = useState(false)
  const [scenarios, setScenarios] = useState<ScenarioSummary[] | null>(null)
  const [restRequests, setRestRequests] = useState<RestDayRequest[]>([])
  const [linkModalOpen, setLinkModalOpen] = useState(false)
  const [personalLink, setPersonalLink] = useState('')
  const [linkMemberName, setLinkMemberName] = useState('')
  const [demandMode, setDemandMode] = useState<'batch' | 'weekday'>('batch')
  const [pdMode, setPdMode] = useState<'batch' | 'weekday'>('batch')
  const [gdMode, setGdMode] = useState<'batch' | 'weekday'>('batch')
  const [faType, setFaType] = useState<string>('rest')
  const [editingFA, setEditingFA] = useState<FixedAssignment | null>(null)
  const [demandEditVisible, setDemandEditVisible] = useState(false)
  const [pdEditVisible, setPdEditVisible] = useState(false)
  const [gdEditVisible, setGdEditVisible] = useState(false)
  const [scenarioViewIdx, setScenarioViewIdx] = useState<number | null>(null)
  const [demandForm] = Form.useForm()
  const [weekdayForm] = Form.useForm()
  const [pdWeekdayForm] = Form.useForm()
  const [gdWeekdayForm] = Form.useForm()
  const [faForm] = Form.useForm()
  const [gdForm] = Form.useForm()
  const [pdForm] = Form.useForm()

  async function load(showSpinner = true) {
    if (!id) return
    if (showSpinner) setLoading(true)
    try {
      const [s, d, fa, m, p, g, gd, pd] = await Promise.all([
        getScheduleResult(id),
        listDemands(id),
        listFixedAssignments(id),
        listMembers(),
        listPatterns(),
        listGroups(),
        listGroupDemands(id),
        listPatternDemands(id),
      ])
      setSchedule(s)
      setDemands(d)
      setFixedAssignments(fa)
      setMembers(m)
      setPatterns(p)
      setGroups(g)
      setGroupDemands(gd)
      setPatternDemands(pd)

      if (s.status === 'requesting') {
        const rr = await listRestRequests(id)
        setRestRequests(rr)
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [id])

  async function handleBatchDemands() {
    const values = await demandForm.validateFields()
    await batchSetDemands(id!, { min_total: values.min_total, max_total: values.max_total })
    message.success('需要設定を更新しました')
    load(false)
  }

  async function handleWeekdayDemands() {
    const values = await weekdayForm.validateFields()
    const settings: Record<number, { min_total: number; max_total: number }> = {}
    for (let wd = 0; wd < 7; wd++) {
      settings[wd] = {
        min_total: values[`min_${wd}`] ?? 0,
        max_total: values[`max_${wd}`] ?? 999,
      }
    }
    await batchSetDemandsByWeekday(id!, settings)
    message.success('曜日別需要を設定しました')
    load(false)
  }

  async function handleClearDemands() {
    await clearDemands(id!)
    message.success('需要設定をクリアしました')
    load(false)
  }

  async function handleBatchPatternDemandAll() {
    const values = await pdForm.validateFields()
    const workPatterns = patterns.filter((p) => p.type === 'work')
    for (const p of workPatterns) {
      const mc = values[`pd_batch_${p.id}`]
      if (mc !== undefined && mc > 0) {
        await batchSetPatternDemand(id!, { pattern_id: p.id, min_count: mc })
      }
    }
    message.success('パターン別需要を設定しました')
    load(false)
  }

  async function handleWeekdayPatternDemandAll() {
    const values = await pdWeekdayForm.validateFields()
    const workPatterns = patterns.filter((p) => p.type === 'work')
    for (const p of workPatterns) {
      const settings: Record<number, { min_count: number }> = {}
      for (let wd = 0; wd < 7; wd++) {
        settings[wd] = { min_count: values[`pd_wd_${p.id}_${wd}`] ?? 0 }
      }
      await batchSetPatternDemandByWeekday(id!, { pattern_id: p.id, weekday_settings: settings })
    }
    message.success('曜日別パターン需要を設定しました')
    load(false)
  }

  async function handleUpdatePatternDemand(demandId: string, minCount: number) {
    await updatePatternDemand(id!, demandId, { min_count: minCount })
    load(false)
  }

  async function handleClearPatternDemands() {
    await clearPatternDemands(id!)
    message.success('パターン別需要をクリアしました')
    load(false)
  }

  async function handleAddFA() {
    const values = await faForm.validateFields()
    await createFixedAssignment(id!, {
      member_id: values.member_id,
      date: values.date.format('YYYY-MM-DD'),
      type: values.type === 'travel' ? 'work' : values.type,
      pattern_id: values.pattern_id || null,
    })
    message.success('固定割当を追加しました')
    faForm.resetFields()
    load(false)
  }

  async function handleEditFA(record: FixedAssignment) {
    setEditingFA(record)
    const pat = record.pattern_id ? patterns.find((p) => p.id === record.pattern_id) : null
    const displayType = pat?.type === 'travel' ? 'travel' : record.type
    setFaType(displayType)
    faForm.setFieldsValue({
      member_id: record.member_id,
      date: null,
      type: displayType,
      pattern_id: record.pattern_id || undefined,
    })
  }

  async function handleUpdateFA() {
    if (!editingFA) return
    const values = await faForm.validateFields()
    await updateFixedAssignment(id!, editingFA.id, {
      member_id: values.member_id,
      date: values.date ? values.date.format('YYYY-MM-DD') : editingFA.date,
      type: values.type === 'travel' ? 'work' : values.type,
      pattern_id: values.pattern_id || null,
    })
    message.success('更新しました')
    setEditingFA(null)
    faForm.resetFields()
    load(false)
  }

  async function handleUpdateDemand(demandId: string, min_total: number, max_total: number) {
    await updateDemand(id!, demandId, { min_total, max_total })
    message.success('更新しました')
    load(false)
  }

  async function handleDeleteFA(assignmentId: string) {
    await deleteFixedAssignment(id!, assignmentId)
    message.success('削除しました')
    load(false)
  }

  async function handleDeleteGD(demandId: string) {
    await deleteGroupDemand(id!, demandId)
    message.success('削除しました')
    load(false)
  }

  async function handleBatchGD() {
    const values = await gdForm.validateFields()
    await batchSetGroupDemand(id!, {
      group_id: values.group_id,
      pattern_id: values.pattern_id || null,
      min_count: values.min_count,
    })
    message.success('グループ需要を一括設定しました')
    gdForm.resetFields()
    load(false)
  }

  async function handleWeekdayGD() {
    const values = await gdWeekdayForm.validateFields()
    const settings: Record<number, { min_count: number }> = {}
    for (let wd = 0; wd < 7; wd++) {
      settings[wd] = { min_count: values[`gd_min_${wd}`] ?? 0 }
    }
    await batchSetGroupDemandByWeekday(id!, { group_id: values.gd_group_id, pattern_id: values.gd_pattern_id || null, weekday_settings: settings })
    message.success('曜日別グループ需要を設定しました')
    gdWeekdayForm.resetFields()
    load(false)
  }

  async function handleUpdateGD(demandId: string, minCount: number) {
    await updateGroupDemand(id!, demandId, { min_count: minCount })
    load(false)
  }

  async function handleClearGD() {
    await clearGroupDemands(id!)
    message.success('グループ需要をクリアしました')
    load(false)
  }

  function getGroupName(groupId: string) {
    return groups.find((g) => g.id === groupId)?.name || groupId
  }

  async function handleCompare() {
    setComparing(true)
    try {
      const result = await compareScenarios(id!)
      setScenarios(result.scenarios)
      message.success('方案比較が完了しました')
    } catch {
      message.error('方案比較に失敗しました')
    } finally {
      setComparing(false)
    }
  }

  async function handleOpenRestRequests() {
    try {
      const result = await openRestRequests(id!)
      message.success(`休み希望受付を開始しました（${result.members_count}名）`)
      load(false)
    } catch {
      message.error('受付開始に失敗しました')
    }
  }

  async function handleCloseRestRequests() {
    try {
      const result = await closeRestRequests(id!)
      message.success(
        `受付を締め切りました。自動提出: ${result.auto_submitted}件、固定割当作成: ${result.fixed_assignments_created}件`,
      )
      load(false)
    } catch {
      message.error('締切処理に失敗しました')
    }
  }

  async function handleShowLink(memberId: string) {
    try {
      const data = await getMemberToken(memberId)
      const member = members.find((m) => m.id === memberId)
      setLinkMemberName(member?.name || '')
      if (data.personal_token) {
        const base = window.location.origin
        setPersonalLink(`${base}/personal/${data.personal_token}`)
      } else {
        setPersonalLink('')
      }
      setLinkModalOpen(true)
    } catch {
      message.error('リンク取得に失敗しました')
    }
  }

  async function handleGenerate() {
    await generateSchedule(id!)
    message.info('スケジュール生成を開始しました...')
    const poll = setInterval(async () => {
      const s = await getScheduleResult(id!)
      setSchedule(s)
      if (s.status === 'completed' || s.status === 'failed') {
        clearInterval(poll)
        if (s.status === 'completed') {
          message.success('生成完了！')
          navigate(`/schedules/${id}/result`)
        } else {
          message.error('生成に失敗しました')
        }
      }
    }, 2000)
  }

  function getMemberName(memberId: string) {
    return members.find((m) => m.id === memberId)?.name || memberId
  }

  function getPatternName(patternId: string | null | undefined) {
    if (!patternId) return '-'
    return patterns.find((p) => p.id === patternId)?.name || patternId
  }

  if (loading || !schedule) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />

  const isRunning = schedule.status === 'running'
  const faColumns = [
    { title: 'メンバー', dataIndex: 'member_id', key: 'member', render: (id: string) => getMemberName(id) },
    { title: '日付', dataIndex: 'date', key: 'date' },
    { title: 'タイプ', key: 'type', render: (_: any, record: FixedAssignment) => {
      const pat = record.pattern_id ? patterns.find((p) => p.id === record.pattern_id) : null
      const isTravel = pat?.type === 'travel'
      if (isTravel) return <Tag color="orange">出張</Tag>
      return <Tag color={record.type === 'work' ? 'blue' : 'green'}>{record.type === 'work' ? '出勤' : '休み'}</Tag>
    }},
    { title: 'パターン', dataIndex: 'pattern_id', key: 'pattern', render: (id: string | null) => getPatternName(id) },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: any, record: FixedAssignment) => (
        <Space>
          <Button size="small" onClick={() => handleEditFA(record)}>編集</Button>
          <Popconfirm title="削除しますか？" onConfirm={() => handleDeleteFA(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/schedules')} style={{ marginBottom: 16 }}>
        スケジュール一覧
      </Button>

      <Typography.Title level={4} editable={{ onChange: async (name) => {
        if (name && name !== schedule.name) {
          await updateSchedule(id!, { name })
          message.success('名前を更新しました')
          load(false)
        }
      }}} style={{ marginBottom: 16 }}>
        {schedule.name || 'スケジュール設定'}
      </Typography.Title>

      <Card title="毎日の必要人数" style={{ marginBottom: 16 }}>
        {demands.length > 0 ? (
          <div style={{ marginBottom: 8 }}>
            <Tag color="blue">設定済み: {demands.length}日間</Tag>
            {(() => {
              const byWd: Record<number, { min: number; max: number }[]> = {}
              demands.forEach((d) => {
                const wd = new Date(d.date).getDay()
                const key = wd === 0 ? 6 : wd - 1
                if (!byWd[key]) byWd[key] = []
                byWd[key].push({ min: d.min_total, max: d.max_total })
              })
              const wdNames = ['月', '火', '水', '木', '金', '土', '日']
              const allSame = demands.every((d) => d.min_total === demands[0].min_total && d.max_total === demands[0].max_total)
              if (allSame) {
                return <span style={{ marginLeft: 8 }}>各日 最小{demands[0]?.min_total}人 〜 最大{demands[0]?.max_total}人</span>
              }
              return (
                <div style={{ marginTop: 4 }}>
                  {Object.entries(byWd).sort(([a], [b]) => Number(a) - Number(b)).map(([wd, vals]) => {
                    const v = vals[0]
                    return <Tag key={wd}>{wdNames[Number(wd)]}: {v.min}〜{v.max}人</Tag>
                  })}
                </div>
              )
            })()}
            <Button size="small" style={{ marginLeft: 8 }} onClick={() => setDemandEditVisible(!demandEditVisible)}>
              {demandEditVisible ? '閉じる' : '日別編集'}
            </Button>
          </div>
        ) : (
          <Tag color="warning">未設定（需要なし = 全員休みになります）</Tag>
        )}
        {demandEditVisible && demands.length > 0 && (
          <Table
            dataSource={demands.map((d) => ({ ...d, key: d.id }))}
            size="small"
            pagination={{ pageSize: 10 }}
            style={{ marginBottom: 12 }}
            columns={[
              { title: '日付', dataIndex: 'date', key: 'date', width: 120 },
              {
                title: '最小', dataIndex: 'min_total', key: 'min',width: 100,
                render: (val: number, record: DailyDemand) => (
                  <InputNumber size="small" min={0} max={99} value={val}
                    onChange={(v) => v !== null && handleUpdateDemand(record.id, v, record.max_total)} />
                ),
              },
              {
                title: '最大', dataIndex: 'max_total', key: 'max', width: 100,
                render: (val: number, record: DailyDemand) => (
                  <InputNumber size="small" min={0} max={99} value={val}
                    onChange={(v) => v !== null && handleUpdateDemand(record.id, record.min_total, v)} />
                ),
              },
            ]}
          />
        )}
        <Space style={{ marginBottom: 8 }}>
          <Select value={demandMode} onChange={setDemandMode} style={{ width: 120 }} options={[
            { label: '一括設定', value: 'batch' },
            { label: '曜日別', value: 'weekday' },
          ]} />
        </Space>
        {demandMode === 'batch' ? (
          <Form form={demandForm} layout="inline" initialValues={{ min_total: 2, max_total: 4 }}>
            <Form.Item name="min_total" label="最小人数" rules={[{ required: true }]}>
              <InputNumber min={0} max={99} />
            </Form.Item>
            <Form.Item name="max_total" label="最大人数" rules={[{ required: true }]}>
              <InputNumber min={1} max={99} />
            </Form.Item>
            <Form.Item>
              <Space>
                <Button type="primary" onClick={handleBatchDemands}>一括設定</Button>
                {demands.length > 0 && (
                  <Popconfirm title="需要設定をクリアしますか？" onConfirm={handleClearDemands}>
                    <Button danger>クリア</Button>
                  </Popconfirm>
                )}
              </Space>
            </Form.Item>
          </Form>
        ) : (
          <Form form={weekdayForm} layout="vertical" initialValues={Object.fromEntries(
            [0,1,2,3,4,5,6].flatMap((wd) => [[`min_${wd}`, wd < 5 ? 3 : 1], [`max_${wd}`, wd < 5 ? 5 : 3]])
          )}>
            <Table
              dataSource={[
                { key: 0, name: '月' }, { key: 1, name: '火' }, { key: 2, name: '水' },
                { key: 3, name: '木' }, { key: 4, name: '金' }, { key: 5, name: '土' }, { key: 6, name: '日' },
              ]}
              pagination={false}
              size="small"
              columns={[
                { title: '曜日', dataIndex: 'name', key: 'name', width: 60 },
                {
                  title: '最小人数', key: 'min',
                  render: (_: any, record: any) => (
                    <Form.Item name={`min_${record.key}`} style={{ margin: 0 }}>
                      <InputNumber min={0} max={99} size="small" />
                    </Form.Item>
                  ),
                },
                {
                  title: '最大人数', key: 'max',
                  render: (_: any, record: any) => (
                    <Form.Item name={`max_${record.key}`} style={{ margin: 0 }}>
                      <InputNumber min={0} max={99} size="small" />
                    </Form.Item>
                  ),
                },
              ]}
            />
            <Space style={{ marginTop: 8 }}>
              <Button type="primary" onClick={handleWeekdayDemands}>曜日別設定</Button>
              {demands.length > 0 && (
                <Popconfirm title="需要設定をクリアしますか？" onConfirm={handleClearDemands}>
                  <Button danger>クリア</Button>
                </Popconfirm>
              )}
            </Space>
          </Form>
        )}
      </Card>

      <Card title="パターン別需要" style={{ marginBottom: 16 }}>
        {(() => {
          const workPatterns = patterns.filter((p) => p.type === 'work')
          if (workPatterns.length === 0) return <Tag color="warning">勤務パターンがありません</Tag>
          const summary = workPatterns.map((p) => {
            const pds = patternDemands.filter((pd) => pd.pattern_id === p.id)
            return pds.length > 0 ? { name: p.name, min: pds[0].min_count, days: pds.length } : null
          }).filter(Boolean) as { name: string; min: number; days: number }[]

          const wdNames = ['月', '火', '水', '木', '金', '土', '日']

          return (
            <>
              {summary.length > 0 && (
                <div style={{ marginBottom: 8 }}>
                  {summary.map((s, i) => (
                    <Tag color="blue" key={i}>{s.name}: 毎日 最小{s.min}人（{s.days}日間）</Tag>
                  ))}
                  <Button size="small" style={{ marginLeft: 8 }} onClick={() => setPdEditVisible(!pdEditVisible)}>
                    {pdEditVisible ? '閉じる' : '日別編集'}
                  </Button>
                </div>
              )}
              {pdEditVisible && patternDemands.length > 0 && (
                <Table
                  dataSource={patternDemands.map((pd) => ({ ...pd, key: pd.id }))}
                  size="small"
                  pagination={{ pageSize: 10 }}
                  style={{ marginBottom: 12 }}
                  columns={[
                    { title: '日付', dataIndex: 'date', key: 'date', width: 120 },
                    { title: 'パターン', dataIndex: 'pattern_id', key: 'pattern', width: 120, render: (id: string) => getPatternName(id) },
                    {
                      title: '最小人数', dataIndex: 'min_count', key: 'min', width: 100,
                      render: (val: number, record: PatternDemand) => (
                        <InputNumber size="small" min={0} max={99} value={val}
                          onChange={(v) => v !== null && handleUpdatePatternDemand(record.id, v)} />
                      ),
                    },
                  ]}
                />
              )}
              <Space style={{ marginBottom: 8 }}>
                <Select value={pdMode} onChange={setPdMode} style={{ width: 120 }} options={[
                  { label: '一括設定', value: 'batch' },
                  { label: '曜日別', value: 'weekday' },
                ]} />
              </Space>
              {pdMode === 'batch' ? (
                <Form form={pdForm} layout="vertical">
                  <Table
                    dataSource={workPatterns.map((p) => ({ key: p.id, name: p.name }))}
                    pagination={false}
                    size="small"
                    columns={[
                      { title: 'パターン', dataIndex: 'name', key: 'name', width: 120 },
                      {
                        title: '最小人数', key: 'min', width: 120,
                        render: (_: any, record: any) => (
                          <Form.Item name={`pd_batch_${record.key}`} style={{ margin: 0 }} initialValue={1}>
                            <InputNumber min={0} max={99} size="small" />
                          </Form.Item>
                        ),
                      },
                    ]}
                  />
                  <Space style={{ marginTop: 8 }}>
                    <Button type="primary" onClick={handleBatchPatternDemandAll}>一括設定</Button>
                    {patternDemands.length > 0 && (
                      <Popconfirm title="全クリアしますか？" onConfirm={handleClearPatternDemands}>
                        <Button danger>クリア</Button>
                      </Popconfirm>
                    )}
                  </Space>
                </Form>
              ) : (
                <Form form={pdWeekdayForm} layout="vertical">
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ borderCollapse: 'collapse', fontSize: 13, marginBottom: 8 }}>
                      <thead>
                        <tr>
                          <th style={{ border: '1px solid #d9d9d9', padding: '4px 8px', background: '#fafafa' }}>パターン</th>
                          {wdNames.map((n, i) => (
                            <th key={i} style={{ border: '1px solid #d9d9d9', padding: '4px 8px', background: '#fafafa', textAlign: 'center' }}>{n}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {workPatterns.map((p) => (
                          <tr key={p.id}>
                            <td style={{ border: '1px solid #d9d9d9', padding: '4px 8px', fontWeight: 500, whiteSpace: 'nowrap' }}>{p.name}</td>
                            {[0,1,2,3,4,5,6].map((wd) => (
                              <td key={wd} style={{ border: '1px solid #d9d9d9', padding: '2px 4px', textAlign: 'center' }}>
                                <Form.Item name={`pd_wd_${p.id}_${wd}`} style={{ margin: 0 }} initialValue={wd < 5 ? 1 : 0}>
                                  <InputNumber min={0} max={99} size="small" style={{ width: 60 }} />
                                </Form.Item>
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <Space style={{ marginTop: 8 }}>
                    <Button type="primary" onClick={handleWeekdayPatternDemandAll}>曜日別設定</Button>
                    {patternDemands.length > 0 && (
                      <Popconfirm title="全クリアしますか？" onConfirm={handleClearPatternDemands}>
                        <Button danger>クリア</Button>
                      </Popconfirm>
                    )}
                  </Space>
                </Form>
              )}
            </>
          )
        })()}
      </Card>

      <Card title="固定割当" style={{ marginBottom: 16 }}>
        <Form form={faForm} layout="inline" style={{ marginBottom: 16 }}>
          <Form.Item name="member_id" label="メンバー" rules={[{ required: true }]}>
            <Select
              style={{ width: 140 }}
              placeholder="選択"
              options={members.map((m) => ({ label: m.name, value: m.id }))}
            />
          </Form.Item>
          <Form.Item name="date" label="日付" rules={[{ required: true }]}>
            <DatePicker />
          </Form.Item>
          <Form.Item name="type" label="タイプ" rules={[{ required: true }]} initialValue="rest">
            <Select style={{ width: 100 }} options={[
              { label: '休み', value: 'rest' },
              { label: '出勤', value: 'work' },
              { label: '出張', value: 'travel' },
            ]} onChange={(v) => { setFaType(v); faForm.setFieldValue('pattern_id', undefined) }} />
          </Form.Item>
          <Form.Item name="pattern_id" label="パターン">
            <Select
              style={{ width: 140 }}
              placeholder="(任意)"
              allowClear
              options={patterns.filter((p) => {
                if (faType === 'work') return p.type === 'work'
                if (faType === 'travel') return p.type === 'travel'
                return p.type === 'rest'
              }).map((p) => ({ label: p.name, value: p.id }))}
            />
          </Form.Item>
          <Form.Item>
            <Space>
              {editingFA ? (
                <>
                  <Button type="primary" onClick={handleUpdateFA}>更新</Button>
                  <Button onClick={() => { setEditingFA(null); faForm.resetFields() }}>キャンセル</Button>
                </>
              ) : (
                <Button type="primary" onClick={handleAddFA}>追加</Button>
              )}
            </Space>
          </Form.Item>
        </Form>
        <Table dataSource={fixedAssignments} columns={faColumns} rowKey="id" size="small" pagination={false} />
      </Card>

      {groups.length > 0 && (
        <Card title="グループ需要" style={{ marginBottom: 16 }}>
          <Space style={{ marginBottom: 8 }}>
            <Select value={gdMode} onChange={setGdMode} style={{ width: 120 }} options={[
              { label: '一括設定', value: 'batch' },
              { label: '曜日別', value: 'weekday' },
            ]} />
          </Space>
          {gdMode === 'batch' ? (
            <Form form={gdForm} layout="inline" style={{ marginBottom: 16 }}>
              <Form.Item name="group_id" label="グループ" rules={[{ required: true }]}>
                <Select
                  style={{ width: 140 }}
                  placeholder="選択"
                  options={groups.map((g) => ({ label: g.name, value: g.id }))}
                />
              </Form.Item>
              <Form.Item name="pattern_id" label="パターン">
                <Select
                  style={{ width: 160 }}
                  placeholder="指定なし（全パターン）"
                  allowClear
                  options={patterns.filter((p) => p.type === 'work').map((p) => ({ label: p.name, value: p.id }))}
                />
              </Form.Item>
              <Form.Item name="min_count" label="最小人数" rules={[{ required: true }]} initialValue={1}>
                <InputNumber min={0} max={99} />
              </Form.Item>
              <Form.Item>
                <Space>
                  <Button type="primary" onClick={handleBatchGD}>一括設定</Button>
                  {groupDemands.length > 0 && (
                    <Popconfirm title="全クリアしますか？" onConfirm={handleClearGD}>
                      <Button danger>クリア</Button>
                    </Popconfirm>
                  )}
                </Space>
              </Form.Item>
            </Form>
          ) : (
            <Form form={gdWeekdayForm} layout="vertical" style={{ marginBottom: 16 }} initialValues={Object.fromEntries(
              [0,1,2,3,4,5,6].map((wd) => [`gd_min_${wd}`, 1])
            )}>
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item name="gd_group_id" label="グループ" rules={[{ required: true }]}>
                    <Select placeholder="選択" options={groups.map((g) => ({ label: g.name, value: g.id }))} />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name="gd_pattern_id" label="パターン">
                    <Select placeholder="指定なし（全パターン）" allowClear options={patterns.filter((p) => p.type === 'work').map((p) => ({ label: p.name, value: p.id }))} />
                  </Form.Item>
                </Col>
              </Row>
              <Table
                dataSource={[
                  { key: 0, name: '月' }, { key: 1, name: '火' }, { key: 2, name: '水' },
                  { key: 3, name: '木' }, { key: 4, name: '金' }, { key: 5, name: '土' }, { key: 6, name: '日' },
                ]}
                pagination={false}
                size="small"
                columns={[
                  { title: '曜日', dataIndex: 'name', key: 'name', width: 60 },
                  {
                    title: '最小人数', key: 'min',
                    render: (_: any, record: any) => (
                      <Form.Item name={`gd_min_${record.key}`} style={{ margin: 0 }}>
                        <InputNumber min={0} max={99} size="small" />
                      </Form.Item>
                    ),
                  },
                ]}
              />
              <Space style={{ marginTop: 8 }}>
                <Button type="primary" onClick={handleWeekdayGD}>曜日別設定</Button>
                {groupDemands.length > 0 && (
                  <Popconfirm title="全クリアしますか？" onConfirm={handleClearGD}>
                    <Button danger>クリア</Button>
                  </Popconfirm>
                )}
              </Space>
            </Form>
          )}
          {groupDemands.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <div style={{ marginBottom: 8 }}>
                <Tag color="blue">設定済み: {groupDemands.length}件</Tag>
                <Button size="small" style={{ marginLeft: 8 }} onClick={() => setGdEditVisible(!gdEditVisible)}>
                  {gdEditVisible ? '閉じる' : '日別編集'}
                </Button>
              </div>
              {gdEditVisible && (
                <Table
                  dataSource={groupDemands.map((d) => ({ ...d, key: d.id }))}
                  size="small"
                  pagination={{ pageSize: 10 }}
                  style={{ marginBottom: 12 }}
                  columns={[
                    { title: '日付', dataIndex: 'date', key: 'date', width: 120 },
                    { title: 'グループ', dataIndex: 'group_id', key: 'group', width: 100, render: (id: string) => getGroupName(id) },
                    { title: 'パターン', dataIndex: 'pattern_id', key: 'pattern', width: 100, render: (id: string | null) => id ? getPatternName(id) : <Tag>全パターン</Tag> },
                    {
                      title: '最小人数', dataIndex: 'min_count', key: 'min', width: 100,
                      render: (val: number, record: GroupDemand) => (
                        <InputNumber size="small" min={0} max={99} value={val}
                          onChange={(v) => v !== null && handleUpdateGD(record.id, v)} />
                      ),
                    },
                    {
                      title: '操作', key: 'actions', width: 60,
                      render: (_: any, record: GroupDemand) => (
                        <Popconfirm title="削除しますか？" onConfirm={() => handleDeleteGD(record.id)}>
                          <Button size="small" danger icon={<DeleteOutlined />} />
                        </Popconfirm>
                      ),
                    },
                  ]}
                />
              )}
            </div>
          )}
        </Card>
      )}

      <Card title="休み希望受付" style={{ marginBottom: 16 }}>
        {schedule.status === 'draft' && (
          <div>
            <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
              受付を開始すると、各メンバーに個人リンクが生成されます。メンバーはリンクからスマートフォンで休み希望日を提出できます。
            </Typography.Text>
            <Button type="primary" icon={<SendOutlined />} onClick={handleOpenRestRequests}>
              休み希望受付を開始
            </Button>
          </div>
        )}

        {schedule.status === 'requesting' && (
          <div>
            <div style={{ marginBottom: 12 }}>
              <Badge status="processing" text="受付中" />
              <span style={{ marginLeft: 16 }}>
                提出済み: {restRequests.filter((r) => r.status === 'submitted').length} / {restRequests.length}名
              </span>
            </div>
            <Table
              dataSource={restRequests}
              rowKey="member_id"
              size="small"
              pagination={false}
              style={{ marginBottom: 16 }}
              columns={[
                { title: 'メンバー', dataIndex: 'member_name', key: 'name' },
                {
                  title: 'ステータス',
                  dataIndex: 'status',
                  key: 'status',
                  render: (s: string) => (
                    <Tag color={s === 'submitted' ? 'green' : 'default'}>
                      {s === 'submitted' ? '提出済み' : '未提出'}
                    </Tag>
                  ),
                },
                {
                  title: '希望日数',
                  key: 'dates',
                  render: (_: any, record: RestDayRequest) => record.requested_dates.length,
                },
                {
                  title: '希望日',
                  key: 'date_list',
                  render: (_: any, record: RestDayRequest) =>
                    record.requested_dates.length > 0
                      ? record.requested_dates.join(', ')
                      : <Typography.Text type="secondary">未設定</Typography.Text>,
                },
                {
                  title: '個人リンク',
                  key: 'link',
                  width: 100,
                  render: (_: any, record: RestDayRequest) => (
                    <Button
                      size="small"
                      icon={<LinkOutlined />}
                      onClick={() => handleShowLink(record.member_id)}
                    >
                      リンク
                    </Button>
                  ),
                },
              ]}
            />
            <Popconfirm
              title="受付を締め切りますか？未提出の希望は自動提出されます。"
              onConfirm={handleCloseRestRequests}
            >
              <Button type="primary" danger icon={<LockOutlined />}>
                受付を締め切る
              </Button>
            </Popconfirm>
          </div>
        )}

        {schedule.status !== 'draft' && schedule.status !== 'requesting' && (
          <Tag color="default">受付終了</Tag>
        )}
      </Card>

      <Modal
        title={`${linkMemberName} の個人リンク`}
        open={linkModalOpen}
        onCancel={() => setLinkModalOpen(false)}
        footer={null}
      >
        {personalLink ? (
          <div>
            <Typography.Paragraph>
              以下のリンクをメンバーに共有してください。このリンクからスマートフォンで休み希望日を提出できます。
            </Typography.Paragraph>
            <div style={{ background: '#f5f5f5', padding: '8px 12px', borderRadius: 4, wordBreak: 'break-all', marginBottom: 12 }}>
              {personalLink}
            </div>
            <Button
              icon={<CopyOutlined />}
              onClick={() => {
                navigator.clipboard.writeText(personalLink)
                message.success('コピーしました')
              }}
            >
              コピー
            </Button>
          </div>
        ) : (
          <Typography.Text type="secondary">リンクが生成されていません</Typography.Text>
        )}
      </Modal>

      <Space style={{ marginTop: 8, marginBottom: 24 }}>
        {isRunning ? (
          <Button type="primary" size="large" disabled icon={<LoadingOutlined spin />}>
            生成中...
          </Button>
        ) : (
          <Button
            type="primary"
            size="large"
            icon={<PlayCircleOutlined />}
            onClick={handleGenerate}
          >
            スケジュール生成
          </Button>
        )}

        <Button
          size="large"
          icon={<ThunderboltOutlined />}
          onClick={handleCompare}
          loading={comparing}
          disabled={isRunning}
        >
          三方案比較
        </Button>

        {schedule.status === 'completed' && (
          <Button
            size="large"
            onClick={() => navigate(`/schedules/${id}/result`)}
          >
            結果を見る
          </Button>
        )}
      </Space>

      {scenarios && (
        <Card title="方案比較結果" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            {scenarios.map((s) => {
              const nameMap: Record<string, string> = {
                balanced: '均衡方案',
                staffing_priority: '人力優先',
                personal_priority: '個人優先',
              }
              const colorMap: Record<string, string> = {
                balanced: '#1677ff',
                staffing_priority: '#fa8c16',
                personal_priority: '#52c41a',
              }
              return (
                <Col span={8} key={s.name}>
                  <Card
                    size="small"
                    title={<Tag color={colorMap[s.name]}>{nameMap[s.name] || s.name}</Tag>}
                    style={{ textAlign: 'center' }}
                  >
                    <Statistic title="健全スコア" value={s.health_score} precision={1} suffix="/ 100" />
                    <Row gutter={8} style={{ marginTop: 12 }}>
                      <Col span={12}>
                        <Statistic title="違反数" value={s.violations_count} valueStyle={{ fontSize: 16, color: s.violations_count > 0 ? '#cf1322' : '#3f8600' }} />
                      </Col>
                      <Col span={12}>
                        <Statistic title="求解時間" value={s.solve_time_seconds} precision={2} suffix="秒" valueStyle={{ fontSize: 16 }} />
                      </Col>
                    </Row>
                    <div style={{ marginTop: 12 }}>
                      {[
                        { label: '個人', key: 'personal' as const, color: '#1677ff' },
                        { label: '需要', key: 'demand' as const, color: '#fa8c16' },
                        { label: '均衡', key: 'balance' as const, color: '#722ed1' },
                      ].map(({ label, key, color }) => (
                        <div key={key} style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
                          <span style={{ width: 40, fontSize: 12 }}>{label}</span>
                          <Progress
                            percent={Math.max(0, 100 - (s.score_breakdown[key] ?? 0))}
                            size="small"
                            strokeColor={color}
                            format={() => `${s.score_breakdown[key] ?? 0}`}
                            style={{ flex: 1 }}
                          />
                        </div>
                      ))}
                    </div>
                    {s.assignments && s.assignments.length > 0 && (
                      <Button size="small" style={{ marginTop: 8 }} onClick={() => setScenarioViewIdx(scenarios!.indexOf(s))}>
                        出勤表を見る
                      </Button>
                    )}
                  </Card>
                </Col>
              )
            })}
          </Row>
        </Card>
      )}

      <Modal
        title={scenarioViewIdx !== null && scenarios ? (() => {
          const nameMap: Record<string, string> = { balanced: '均衡方案', staffing_priority: '人力優先', personal_priority: '個人優先' }
          return `${nameMap[scenarios[scenarioViewIdx].name] || scenarios[scenarioViewIdx].name} - 出勤表`
        })() : '出勤表'}
        open={scenarioViewIdx !== null}
        onCancel={() => setScenarioViewIdx(null)}
        footer={null}
        width="90vw"
        styles={{ body: { overflowX: 'auto' } }}
      >
        {scenarioViewIdx !== null && scenarios && (() => {
          const sc = scenarios[scenarioViewIdx]
          if (!sc.assignments || sc.assignments.length === 0) return <Typography.Text type="secondary">割当データなし</Typography.Text>
          const memberIds = [...new Set(sc.assignments.map((a) => a.member_id))]
          const dates = [...new Set(sc.assignments.map((a) => a.date))].sort()
          const lookup = new Map<string, typeof sc.assignments[0]>()
          sc.assignments.forEach((a) => lookup.set(`${a.member_id}_${a.date}`, a))
          const memberNameMap = new Map(sc.assignments.map((a) => [a.member_id, a.member_name]))
          return (
            <table style={{ borderCollapse: 'collapse', fontSize: 12, width: '100%' }}>
              <thead>
                <tr>
                  <th style={{ border: '1px solid #d9d9d9', padding: '4px 8px', position: 'sticky', left: 0, background: '#fafafa', zIndex: 1 }}>メンバー</th>
                  {dates.map((d) => {
                    const dt = new Date(d)
                    const wd = ['日','月','火','水','木','金','土'][dt.getDay()]
                    return <th key={d} style={{ border: '1px solid #d9d9d9', padding: '4px 6px', whiteSpace: 'nowrap', background: dt.getDay() === 0 || dt.getDay() === 6 ? '#fff1f0' : '#fafafa' }}>{`${dt.getMonth()+1}/${dt.getDate()}(${wd})`}</th>
                  })}
                </tr>
              </thead>
              <tbody>
                {memberIds.map((mid) => (
                  <tr key={mid}>
                    <td style={{ border: '1px solid #d9d9d9', padding: '4px 8px', position: 'sticky', left: 0, background: '#fff', zIndex: 1, fontWeight: 500, whiteSpace: 'nowrap' }}>{memberNameMap.get(mid) || mid}</td>
                    {dates.map((d) => {
                      const a = lookup.get(`${mid}_${d}`)
                      const isRest = a?.is_rest
                      return (
                        <td key={d} style={{ border: '1px solid #d9d9d9', padding: '4px 6px', textAlign: 'center', background: isRest ? '#f6ffed' : '#fff', color: isRest ? '#389e0d' : '#1677ff', fontWeight: 500 }}>
                          {a ? (isRest ? '休' : a.pattern_name) : '-'}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          )
        })()}
      </Modal>
    </div>
  )
}
