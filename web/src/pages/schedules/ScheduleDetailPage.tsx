import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Button, InputNumber, Form, Table, Select, Space, Tag, message, Popconfirm, DatePicker, Spin, Row, Col, Statistic, Progress, Modal, Typography, Badge } from 'antd'
import { PlayCircleOutlined, ArrowLeftOutlined, DeleteOutlined, LoadingOutlined, ThunderboltOutlined, SendOutlined, LockOutlined, CopyOutlined, LinkOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { getScheduleResult, generateSchedule, compareScenarios, type ScheduleResult, type ScenarioSummary } from '../../api/schedules'
import { listDemands, batchSetDemands, clearDemands, type DailyDemand } from '../../api/demands'
import { listFixedAssignments, createFixedAssignment, deleteFixedAssignment, type FixedAssignment } from '../../api/fixed-assignments'
import { listMembers, type Member } from '../../api/members'
import { listPatterns, type Pattern } from '../../api/patterns'
import { listGroups, listGroupDemands, createGroupDemand, deleteGroupDemand, type Group, type GroupDemand } from '../../api/groups'
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
  const [loading, setLoading] = useState(true)
  const [comparing, setComparing] = useState(false)
  const [scenarios, setScenarios] = useState<ScenarioSummary[] | null>(null)
  const [restRequests, setRestRequests] = useState<RestDayRequest[]>([])
  const [linkModalOpen, setLinkModalOpen] = useState(false)
  const [personalLink, setPersonalLink] = useState('')
  const [linkMemberName, setLinkMemberName] = useState('')
  const [demandForm] = Form.useForm()
  const [faForm] = Form.useForm()
  const [gdForm] = Form.useForm()

  async function load() {
    if (!id) return
    setLoading(true)
    try {
      const [s, d, fa, m, p, g, gd] = await Promise.all([
        getScheduleResult(id),
        listDemands(id),
        listFixedAssignments(id),
        listMembers(),
        listPatterns(),
        listGroups(),
        listGroupDemands(id),
      ])
      setSchedule(s)
      setDemands(d)
      setFixedAssignments(fa)
      setMembers(m)
      setPatterns(p)
      setGroups(g)
      setGroupDemands(gd)

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
    load()
  }

  async function handleClearDemands() {
    await clearDemands(id!)
    message.success('需要設定をクリアしました')
    load()
  }

  async function handleAddFA() {
    const values = await faForm.validateFields()
    await createFixedAssignment(id!, {
      member_id: values.member_id,
      date: values.date.format('YYYY-MM-DD'),
      type: values.type,
      pattern_id: values.pattern_id || null,
    })
    message.success('固定割当を追加しました')
    faForm.resetFields()
    load()
  }

  async function handleDeleteFA(assignmentId: string) {
    await deleteFixedAssignment(id!, assignmentId)
    message.success('削除しました')
    load()
  }

  async function handleAddGD() {
    const values = await gdForm.validateFields()
    await createGroupDemand(id!, {
      date: values.date.format('YYYY-MM-DD'),
      group_id: values.group_id,
      pattern_id: values.pattern_id,
      min_count: values.min_count,
    })
    message.success('グループ需要を追加しました')
    gdForm.resetFields()
    load()
  }

  async function handleDeleteGD(demandId: string) {
    await deleteGroupDemand(id!, demandId)
    message.success('削除しました')
    load()
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
      load()
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
      load()
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
  const isEditable = !isRunning

  const faColumns = [
    { title: 'メンバー', dataIndex: 'member_id', key: 'member', render: (id: string) => getMemberName(id) },
    { title: '日付', dataIndex: 'date', key: 'date' },
    { title: 'タイプ', dataIndex: 'type', key: 'type', render: (t: string) => <Tag color={t === 'work' ? 'blue' : 'green'}>{t === 'work' ? '出勤' : '休み'}</Tag> },
    { title: 'パターン', dataIndex: 'pattern_id', key: 'pattern', render: (id: string | null) => getPatternName(id) },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      render: (_: any, record: FixedAssignment) => (
        <Popconfirm title="削除しますか？" onConfirm={() => handleDeleteFA(record.id)}>
          <Button size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ]

  return (
    <div>
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/schedules')} style={{ marginBottom: 16 }}>
        スケジュール一覧
      </Button>

      <h2>スケジュール設定</h2>

      <Card title="毎日の必要人数" style={{ marginBottom: 16 }}>
        {demands.length > 0 ? (
          <div style={{ marginBottom: 8 }}>
            <Tag color="blue">設定済み: {demands.length}日間</Tag>
            <span style={{ marginLeft: 8 }}>
              各日 最小{demands[0]?.min_total}人 〜 最大{demands[0]?.max_total}人
            </span>
          </div>
        ) : (
          <Tag color="warning">未設定（需要なし = 全員休みになります）</Tag>
        )}
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
            ]} />
          </Form.Item>
          <Form.Item name="pattern_id" label="パターン">
            <Select
              style={{ width: 140 }}
              placeholder="(任意)"
              allowClear
              options={patterns.map((p) => ({ label: p.name, value: p.id }))}
            />
          </Form.Item>
          <Form.Item>
            <Button type="primary" onClick={handleAddFA}>追加</Button>
          </Form.Item>
        </Form>
        <Table dataSource={fixedAssignments} columns={faColumns} rowKey="id" size="small" pagination={false} />
      </Card>

      {groups.length > 0 && (
        <Card title="グループ需要" style={{ marginBottom: 16 }}>
          <Form form={gdForm} layout="inline" style={{ marginBottom: 16 }}>
            <Form.Item name="group_id" label="グループ" rules={[{ required: true }]}>
              <Select
                style={{ width: 140 }}
                placeholder="選択"
                options={groups.map((g) => ({ label: g.name, value: g.id }))}
              />
            </Form.Item>
            <Form.Item name="date" label="日付" rules={[{ required: true }]}>
              <DatePicker />
            </Form.Item>
            <Form.Item name="pattern_id" label="パターン" rules={[{ required: true }]}>
              <Select
                style={{ width: 140 }}
                placeholder="選択"
                options={patterns.map((p) => ({ label: p.name, value: p.id }))}
              />
            </Form.Item>
            <Form.Item name="min_count" label="最小人数" rules={[{ required: true }]} initialValue={1}>
              <InputNumber min={0} max={99} />
            </Form.Item>
            <Form.Item>
              <Button type="primary" onClick={handleAddGD}>追加</Button>
            </Form.Item>
          </Form>
          <Table
            dataSource={groupDemands}
            rowKey="id"
            size="small"
            pagination={false}
            columns={[
              { title: 'グループ', dataIndex: 'group_id', key: 'group', render: (id: string) => getGroupName(id) },
              { title: '日付', dataIndex: 'date', key: 'date' },
              { title: 'パターン', dataIndex: 'pattern_id', key: 'pattern', render: (id: string) => getPatternName(id) },
              { title: '最小人数', dataIndex: 'min_count', key: 'min_count' },
              {
                title: '操作', key: 'actions', width: 80,
                render: (_: any, record: GroupDemand) => (
                  <Popconfirm title="削除しますか？" onConfirm={() => handleDeleteGD(record.id)}>
                    <Button size="small" danger icon={<DeleteOutlined />} />
                  </Popconfirm>
                ),
              },
            ]}
          />
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
                  </Card>
                </Col>
              )
            })}
          </Row>
        </Card>
      )}
    </div>
  )
}
