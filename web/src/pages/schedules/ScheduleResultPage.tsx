import { useEffect, useState } from 'react'
import { Button, Card, Table, Tag, Statistic, Row, Col, Alert, Spin, Progress, Collapse, List, Typography, Space, Upload, Modal, message } from 'antd'
import { DownloadOutlined, FilePdfOutlined, UploadOutlined } from '@ant-design/icons'
import { useParams, useNavigate } from 'react-router-dom'
import { getScheduleResult, exportExcel, exportPdf, previewScheduleImport, executeScheduleImport, type ScheduleResult, type Assignment, type Violation, type ScheduleImportPreview } from '../../api/schedules'
import { listMembers } from '../../api/members'
import { listPatterns } from '../../api/patterns'
import { listGroups, listGroupDemands, type Group, type GroupDemand } from '../../api/groups'
import { listDemands, listPatternDemands, type DailyDemand, type PatternDemand } from '../../api/demands'

const { Text } = Typography

const CONSTRAINT_LABELS: Record<string, string> = {
  daily_demand_min: '毎日需要（最小）',
  daily_demand_max: '毎日需要（最大）',
  period_days_min: '期間出勤日数（最小）',
  period_days_max: '期間出勤日数（最大）',
  weekly_days_min: '週出勤日数（最小）',
  weekly_days_max: '週出勤日数（最大）',
  period_hours_min: '期間労働時間（最小）',
  period_hours_max: '期間労働時間（最大）',
  weekly_hours_min: '週労働時間（最小）',
  weekly_hours_max: '週労働時間（最大）',
  consecutive_work: '連続出勤超過',
  consecutive_rest: '連続休息超過',
  group_demand_min: 'グループ需要（最小）',
}

const GROUP_LABELS: Record<string, { text: string; color: string }> = {
  personal: { text: '個人制約', color: 'blue' },
  demand: { text: '需要制約', color: 'orange' },
  group: { text: 'グループ制約', color: 'green' },
}

export default function ScheduleResultPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [result, setResult] = useState<ScheduleResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [members, setMembers] = useState<Record<string, string>>({})
  const [patterns, setPatterns] = useState<Record<string, { name: string; color: string; work_hours: number; type: string }>>({})
  const [groupNames, setGroupNames] = useState<Record<string, string>>({})
  const [groupsData, setGroupsData] = useState<Group[]>([])
  const [dailyDemands, setDailyDemands] = useState<DailyDemand[]>([])
  const [patternDemands, setPatternDemands] = useState<PatternDemand[]>([])
  const [groupDemands, setGroupDemands] = useState<GroupDemand[]>([])
  const [showDaily, setShowDaily] = useState(false)
  const [showPatternDemand, setShowPatternDemand] = useState(false)
  const [showGroupDemand, setShowGroupDemand] = useState(false)
  const [showPersonal, setShowPersonal] = useState(false)
  const [showBalance, setShowBalance] = useState(false)
  const [importModalOpen, setImportModalOpen] = useState(false)
  const [importPreview, setImportPreview] = useState<ScheduleImportPreview | null>(null)
  const [importFile, setImportFile] = useState<File | null>(null)
  const [importing, setImporting] = useState(false)

  useEffect(() => {
    async function load() {
      if (!id) return
      const [r, mList, pList, gList, dd, pd, gd] = await Promise.all([
        getScheduleResult(id),
        listMembers(),
        listPatterns(),
        listGroups(),
        listDemands(id),
        listPatternDemands(id),
        listGroupDemands(id),
      ])
      setResult(r)
      setMembers(Object.fromEntries(mList.map((m) => [m.id, m.name])))
      setPatterns(Object.fromEntries(pList.map((p) => [p.id, { name: p.name, color: p.color_code, work_hours: p.work_hours ?? 0, type: p.type }])))
      setGroupNames(Object.fromEntries(gList.map((g) => [g.id, g.name])))
      setGroupsData(gList)
      setDailyDemands(dd)
      setPatternDemands(pd)
      setGroupDemands(gd)
      setLoading(false)
    }
    load()
  }, [id])

  async function handleImportFile(file: File) {
    if (!id) return false
    setImportFile(file)
    try {
      const preview = await previewScheduleImport(id, file)
      setImportPreview(preview)
      setImportModalOpen(true)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'プレビューに失敗しました')
    }
    return false
  }

  async function handleImportExecute() {
    if (!importFile || !id) return
    setImporting(true)
    try {
      const result = await executeScheduleImport(id, importFile)
      message.success(`${result.applied} 件の変更を反映しました`)
      setImportModalOpen(false)
      setImportFile(null)
      setImportPreview(null)
      const [r, mList, pList, gList, dd, pd2, gd2] = await Promise.all([
        getScheduleResult(id),
        listMembers(),
        listPatterns(),
        listGroups(),
        listDemands(id),
        listPatternDemands(id),
        listGroupDemands(id),
      ])
      setResult(r)
      setMembers(Object.fromEntries(mList.map((m) => [m.id, m.name])))
      setPatterns(Object.fromEntries(pList.map((p) => [p.id, { name: p.name, color: p.color_code, work_hours: p.work_hours ?? 0, type: p.type }])))
      setGroupNames(Object.fromEntries(gList.map((g) => [g.id, g.name])))
      setGroupsData(gList)
      setDailyDemands(dd)
      setPatternDemands(pd2)
      setGroupDemands(gd2)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'インポートに失敗しました')
    } finally {
      setImporting(false)
    }
  }

  function resolveIds(text: string): string {
    return text.replace(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi, (uuid) => {
      if (members[uuid]) return members[uuid]
      if (patterns[uuid]) return patterns[uuid].name
      if (groupNames[uuid]) return groupNames[uuid]
      return uuid
    })
  }

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />
  if (!result) return <Alert type="error" message="スケジュールが見つかりません" />

  const dates = [...new Set(result.assignments?.map((a) => a.date) || [])].sort()
  const memberIds = [...new Set(result.assignments?.map((a) => a.member_id) || [])]

  const gridData = memberIds.map((mid) => {
    const row: Record<string, any> = { key: mid, member: members[mid] || mid }
    for (const d of dates) {
      const a = result.assignments?.find((x) => x.member_id === mid && x.date === d)
      row[d] = a
    }
    return row
  })

  const gridColumns = [
    { title: 'メンバー', dataIndex: 'member', key: 'member', fixed: 'left' as const, width: 100 },
    ...dates.map((d) => {
      const dt = new Date(d)
      const wdNames = ['日','月','火','水','木','金','土']
      const wd = wdNames[dt.getDay()]
      const isWeekend = dt.getDay() === 0 || dt.getDay() === 6
      return {
      title: <span style={{ color: isWeekend ? '#cf1322' : undefined }}>{`${dt.getMonth()+1}/${dt.getDate()}`}<br/><span style={{ fontSize: 10 }}>{wd}</span></span>,
      dataIndex: d,
      key: d,
      width: 70,
      render: (a: Assignment | undefined) => {
        if (!a) return '-'
        if (a.is_rest) return <Tag>休み</Tag>
        const p = a.pattern_id ? patterns[a.pattern_id] : null
        return (
          <Tag color={p?.color || undefined}>
            {p?.name || a.pattern_name}
          </Tag>
        )
      },
    }}),
  ]

  const violations = result.violations || []

  const violationColumns = [
    {
      title: 'グループ',
      dataIndex: 'constraint_group',
      key: 'group',
      width: 120,
      render: (g: string) => {
        const info = GROUP_LABELS[g] || { text: g, color: 'default' }
        return <Tag color={info.color}>{info.text}</Tag>
      },
    },
    {
      title: '制約種別',
      dataIndex: 'constraint_type',
      key: 'type',
      render: (t: string) => CONSTRAINT_LABELS[t] || t,
    },
    {
      title: '優先度',
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
      render: (p: string) => <Tag color={p <= 'P3' ? 'red' : p <= 'P6' ? 'orange' : 'blue'}>{p}</Tag>,
    },
    {
      title: 'メンバー',
      dataIndex: 'target_member_id',
      key: 'member',
      width: 100,
      render: (mid: string | undefined) => mid ? (members[mid] || mid) : '-',
    },
    {
      title: '対象日',
      dataIndex: 'target_date',
      key: 'date',
      width: 100,
      render: (d: string | undefined) => d || '-',
    },
    {
      title: '設定値',
      dataIndex: 'setting_value',
      key: 'setting',
      render: (v: string | undefined) => v ? resolveIds(v) : '-',
    },
    {
      title: '実績値',
      dataIndex: 'actual_value',
      key: 'actual',
      width: 80,
    },
  ]

  function renderViolationDetail(v: Violation) {
    const hasFactors = v.contributing_factors && v.contributing_factors.length > 0
    const hasSuggestions = v.suggestions && v.suggestions.length > 0
    if (!hasFactors && !hasSuggestions) return null

    return (
      <div style={{ padding: '8px 16px' }}>
        {hasFactors && (
          <div style={{ marginBottom: 8 }}>
            <Text strong>原因分析:</Text>
            <List
              size="small"
              dataSource={v.contributing_factors}
              renderItem={(item) => <List.Item style={{ padding: '2px 0' }}>・{item}</List.Item>}
            />
          </div>
        )}
        {hasSuggestions && (
          <div>
            <Text strong>改善提案:</Text>
            <List
              size="small"
              dataSource={v.suggestions}
              renderItem={(item) => <List.Item style={{ padding: '2px 0', color: '#1677ff' }}>💡 {item}</List.Item>}
            />
          </div>
        )}
      </div>
    )
  }

  const groupedViolations = violations.reduce<Record<string, Violation[]>>((acc, v) => {
    const g = v.constraint_group || 'other'
    if (!acc[g]) acc[g] = []
    acc[g].push(v)
    return acc
  }, {})

  return (
    <>
      <Space style={{ marginBottom: 16 }}>
        <Button onClick={() => navigate(`/schedules/${id}`)}>
          設定に戻る
        </Button>
        <Button
          icon={<DownloadOutlined />}
          onClick={async () => {
            try {
              await exportExcel(id!)
              message.success('Excelをダウンロードしました')
            } catch {
              message.error('ダウンロードに失敗しました')
            }
          }}
        >
          Excel出力
        </Button>
        <Button
          icon={<FilePdfOutlined />}
          onClick={async () => {
            try {
              await exportPdf(id!)
              message.success('PDFをダウンロードしました')
            } catch {
              message.error('ダウンロードに失敗しました')
            }
          }}
        >
          PDF出力
        </Button>
        <Upload accept=".xlsx,.xls" showUploadList={false} beforeUpload={handleImportFile}>
          <Button icon={<UploadOutlined />}>Excel取込</Button>
        </Upload>
      </Space>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card><Statistic title="健全スコア" value={result.health_score ?? 0} suffix="/ 100" precision={1} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="ステータス" value={result.result_status || result.status} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="求解時間" value={result.solve_time_seconds ?? 0} suffix="秒" precision={2} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="違反数" value={violations.length} valueStyle={{ color: violations.length > 0 ? '#cf1322' : '#3f8600' }} /></Card>
        </Col>
      </Row>

      {result.score_breakdown && (
        <Card title="スコア明細" style={{ marginBottom: 24 }}>
          <Row gutter={16}>
            {[
              { label: '個人制約', key: 'personal', color: '#1677ff' },
              { label: 'グループ需要', key: 'group', color: '#52c41a' },
              { label: '毎日需要', key: 'demand', color: '#fa8c16' },
              { label: '均衡性', key: 'balance', color: '#722ed1' },
            ].map(({ label, key, color }) => {
              const score = (result.score_breakdown as any)?.[key] ?? 0
              return (
                <Col span={6} key={key}>
                  <div style={{ textAlign: 'center', marginBottom: 8 }}>
                    <div style={{ fontWeight: 500, marginBottom: 4 }}>{label}</div>
                    <Progress
                      type="circle"
                      size={80}
                      percent={score}
                      strokeColor={score >= 80 ? color : score >= 50 ? '#faad14' : '#ff4d4f'}
                      format={() => `${score}`}
                    />
                  </div>
                </Col>
              )
            })}
          </Row>
        </Card>
      )}

      <Card title="排班表" style={{ marginBottom: 24 }}>
        <Table
          dataSource={gridData}
          columns={gridColumns}
          pagination={false}
          scroll={{ x: 'max-content' }}
          size="small"
          bordered
        />
      </Card>

      <Space style={{ marginBottom: 16 }} wrap>
        <Button type={showDaily ? 'primary' : 'default'} onClick={() => setShowDaily(!showDaily)}>日別統計</Button>
        <Button type={showPatternDemand ? 'primary' : 'default'} onClick={() => setShowPatternDemand(!showPatternDemand)}>パターン別需要</Button>
        <Button type={showGroupDemand ? 'primary' : 'default'} onClick={() => setShowGroupDemand(!showGroupDemand)}>グループ需要</Button>
        <Button type={showPersonal ? 'primary' : 'default'} onClick={() => setShowPersonal(!showPersonal)}>個人統計</Button>
        <Button type={showBalance ? 'primary' : 'default'} onClick={() => setShowBalance(!showBalance)}>全体バランス</Button>
      </Space>

      {showDaily && (() => {
        const demandMap = new Map(dailyDemands.map((d) => [d.date, d]))
        const rows = [
          { key: 'actual', label: '出勤人数' },
          { key: 'required', label: '必要人数' },
          { key: 'diff', label: '過不足' },
        ]
        return (
          <Card title="日別出勤統計" size="small" style={{ marginBottom: 16 }}>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ borderCollapse: 'collapse', fontSize: 12, width: '100%' }}>
                <thead>
                  <tr>
                    <th style={{ border: '1px solid #d9d9d9', padding: '4px 8px', background: '#fafafa', position: 'sticky', left: 0, zIndex: 1 }}>項目</th>
                    {dates.map((d) => {
                      const dt = new Date(d)
                      const isWeekend = dt.getDay() === 0 || dt.getDay() === 6
                      return <th key={d} style={{ border: '1px solid #d9d9d9', padding: '4px 4px', background: isWeekend ? '#fff1f0' : '#fafafa', whiteSpace: 'nowrap', fontSize: 11 }}>{`${dt.getMonth()+1}/${dt.getDate()}`}</th>
                    })}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.key}>
                      <td style={{ border: '1px solid #d9d9d9', padding: '4px 8px', fontWeight: 500, whiteSpace: 'nowrap', position: 'sticky', left: 0, background: '#fff', zIndex: 1 }}>{row.label}</td>
                      {dates.map((d) => {
                        const assignments = result.assignments?.filter((a) => a.date === d) || []
                        const actual = assignments.filter((a) => !a.is_rest).length
                        const demand = demandMap.get(d)
                        let content: React.ReactNode = '-'
                        let bg = '#fff'
                        if (row.key === 'actual') {
                          content = actual
                        } else if (row.key === 'required') {
                          content = demand ? `${demand.min_total}~${demand.max_total}` : '-'
                        } else if (row.key === 'diff') {
                          if (demand) {
                            const diff = actual - demand.min_total
                            content = diff >= 0 ? `+${diff}` : `${diff}`
                            bg = diff >= 0 ? '#f6ffed' : '#fff2f0'
                          }
                        }
                        return <td key={d} style={{ border: '1px solid #d9d9d9', padding: '4px 4px', textAlign: 'center', background: bg, fontSize: 11 }}>{content}</td>
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )
      })()}

      {showPatternDemand && (() => {
        const pdByPattern = new Map<string, Map<string, number>>()
        patternDemands.forEach((pd) => {
          if (!pdByPattern.has(pd.pattern_id)) pdByPattern.set(pd.pattern_id, new Map())
          pdByPattern.get(pd.pattern_id)!.set(pd.date, pd.min_count)
        })
        if (pdByPattern.size === 0) return <Card title="パターン別需要充足" size="small" style={{ marginBottom: 16 }}><Text type="secondary">パターン別需要の設定なし</Text></Card>
        return (
          <Card title="パターン別需要充足" size="small" style={{ marginBottom: 16 }}>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ borderCollapse: 'collapse', fontSize: 12, width: '100%' }}>
                <thead>
                  <tr>
                    <th style={{ border: '1px solid #d9d9d9', padding: '4px 8px', background: '#fafafa', position: 'sticky', left: 0, zIndex: 1 }}>パターン</th>
                    {dates.map((d) => {
                      const dt = new Date(d)
                      const isWeekend = dt.getDay() === 0 || dt.getDay() === 6
                      return <th key={d} style={{ border: '1px solid #d9d9d9', padding: '4px 4px', background: isWeekend ? '#fff1f0' : '#fafafa', whiteSpace: 'nowrap', fontSize: 11 }}>{`${dt.getMonth()+1}/${dt.getDate()}`}</th>
                    })}
                  </tr>
                </thead>
                <tbody>
                  {[...pdByPattern.entries()].map(([patId, dateMap]) => (
                    <tr key={patId}>
                      <td style={{ border: '1px solid #d9d9d9', padding: '4px 8px', fontWeight: 500, whiteSpace: 'nowrap', position: 'sticky', left: 0, background: '#fff', zIndex: 1 }}>{patterns[patId]?.name || patId}</td>
                      {dates.map((d) => {
                        const required = dateMap.get(d)
                        if (required === undefined) return <td key={d} style={{ border: '1px solid #d9d9d9', padding: '4px 4px', textAlign: 'center', fontSize: 11 }}>-</td>
                        const actual = (result.assignments?.filter((a) => a.date === d && a.pattern_id === patId) || []).length
                        const ok = actual >= required
                        return <td key={d} style={{ border: '1px solid #d9d9d9', padding: '4px 4px', textAlign: 'center', background: ok ? '#f6ffed' : '#fff2f0', color: ok ? '#389e0d' : '#cf1322', fontWeight: 500, fontSize: 11 }}>{`${actual}/${required}`}</td>
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )
      })()}

      {showGroupDemand && (() => {
        if (groupDemands.length === 0) return <Card title="グループ需要充足" size="small" style={{ marginBottom: 16 }}><Text type="secondary">グループ需要の設定なし</Text></Card>
        const combos = new Map<string, { groupId: string; patternId: string | null; label: string; dateMap: Map<string, number> }>()
        groupDemands.forEach((gd) => {
          const key = `${gd.group_id}_${gd.pattern_id || 'any'}`
          if (!combos.has(key)) {
            const gName = groupNames[gd.group_id] || gd.group_id
            const pName = gd.pattern_id ? (patterns[gd.pattern_id]?.name || gd.pattern_id) : '全パターン'
            combos.set(key, { groupId: gd.group_id, patternId: gd.pattern_id || null, label: `${gName}(${pName})`, dateMap: new Map() })
          }
          combos.get(key)!.dateMap.set(gd.date, gd.min_count)
        })
        return (
          <Card title="グループ需要充足" size="small" style={{ marginBottom: 16 }}>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ borderCollapse: 'collapse', fontSize: 12, width: '100%' }}>
                <thead>
                  <tr>
                    <th style={{ border: '1px solid #d9d9d9', padding: '4px 8px', background: '#fafafa', position: 'sticky', left: 0, zIndex: 1 }}>グループ</th>
                    {dates.map((d) => {
                      const dt = new Date(d)
                      const isWeekend = dt.getDay() === 0 || dt.getDay() === 6
                      return <th key={d} style={{ border: '1px solid #d9d9d9', padding: '4px 4px', background: isWeekend ? '#fff1f0' : '#fafafa', whiteSpace: 'nowrap', fontSize: 11 }}>{`${dt.getMonth()+1}/${dt.getDate()}`}</th>
                    })}
                  </tr>
                </thead>
                <tbody>
                  {[...combos.values()].map((combo) => {
                    const groupMembers = groupsData.find((g) => g.id === combo.groupId)?.member_ids || []
                    return (
                      <tr key={combo.label}>
                        <td style={{ border: '1px solid #d9d9d9', padding: '4px 8px', fontWeight: 500, whiteSpace: 'nowrap', position: 'sticky', left: 0, background: '#fff', zIndex: 1 }}>{combo.label}</td>
                        {dates.map((d) => {
                          const required = combo.dateMap.get(d)
                          if (required === undefined) return <td key={d} style={{ border: '1px solid #d9d9d9', padding: '4px 4px', textAlign: 'center', fontSize: 11 }}>-</td>
                          const dayAssignments = result.assignments?.filter((a) => a.date === d && groupMembers.includes(a.member_id) && !a.is_rest) || []
                          let actual: number
                          if (combo.patternId) {
                            actual = dayAssignments.filter((a) => a.pattern_id === combo.patternId).length
                          } else {
                            actual = dayAssignments.length
                          }
                          const ok = actual >= required
                          return <td key={d} style={{ border: '1px solid #d9d9d9', padding: '4px 4px', textAlign: 'center', background: ok ? '#f6ffed' : '#fff2f0', color: ok ? '#389e0d' : '#cf1322', fontWeight: 500, fontSize: 11 }}>{`${actual}/${required}`}</td>
                        })}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        )
      })()}

      {showPersonal && (() => {
        const workPatternIds = Object.entries(patterns).filter(([, p]) => p.type === 'work' || p.type === 'travel').map(([id]) => id)
        const memberStats = memberIds.map((mid) => {
          const memberAssignments = result.assignments?.filter((a) => a.member_id === mid) || []
          const workDays = memberAssignments.filter((a) => !a.is_rest).length
          const restDays = memberAssignments.filter((a) => a.is_rest).length
          let totalHours = 0
          const patternCounts: Record<string, number> = {}
          memberAssignments.forEach((a) => {
            if (!a.is_rest && a.pattern_id) {
              const p = patterns[a.pattern_id]
              if (p) {
                totalHours += p.work_hours
                patternCounts[p.name] = (patternCounts[p.name] || 0) + 1
              }
            }
          })
          return { mid, name: members[mid] || mid, workDays, restDays, totalHours: Math.round(totalHours * 10) / 10, patternCounts }
        })
        return (
          <Card title="個人統計" size="small" style={{ marginBottom: 16 }}>
            <Table
              dataSource={memberStats.map((s) => ({ ...s, key: s.mid }))}
              size="small"
              pagination={false}
              columns={[
                { title: 'メンバー', dataIndex: 'name', key: 'name', width: 100, fixed: 'left' as const },
                { title: '出勤', dataIndex: 'workDays', key: 'work', width: 60, sorter: (a: any, b: any) => a.workDays - b.workDays },
                { title: '休日', dataIndex: 'restDays', key: 'rest', width: 60, sorter: (a: any, b: any) => a.restDays - b.restDays },
                { title: '労働時間', dataIndex: 'totalHours', key: 'hours', width: 80, sorter: (a: any, b: any) => a.totalHours - b.totalHours, render: (v: number) => `${v}h` },
                ...workPatternIds.map((pid) => ({
                  title: patterns[pid]?.name || pid,
                  key: pid,
                  width: 60,
                  render: (_: any, record: any) => record.patternCounts[patterns[pid]?.name] || 0,
                })),
              ]}
              scroll={{ x: 'max-content' }}
            />
          </Card>
        )
      })()}

      {showBalance && (() => {
        const memberStats = memberIds.map((mid) => {
          const ma = result.assignments?.filter((a) => a.member_id === mid) || []
          const workDays = ma.filter((a) => !a.is_rest).length
          let totalHours = 0
          ma.forEach((a) => {
            if (!a.is_rest && a.pattern_id && patterns[a.pattern_id]) {
              totalHours += patterns[a.pattern_id].work_hours
            }
          })
          return { workDays, totalHours }
        })
        if (memberStats.length === 0) return null
        const workDaysList = memberStats.map((s) => s.workDays)
        const hoursList = memberStats.map((s) => s.totalHours)
        const avg = (arr: number[]) => arr.reduce((a, b) => a + b, 0) / arr.length
        const stddev = (arr: number[]) => { const m = avg(arr); return Math.sqrt(arr.reduce((s, v) => s + (v - m) ** 2, 0) / arr.length) }
        return (
          <Card title="全体バランス" size="small" style={{ marginBottom: 16 }}>
            <Row gutter={24}>
              <Col span={8}>
                <Statistic title="出勤日数（平均）" value={avg(workDaysList).toFixed(1)} suffix="日" />
                <div style={{ fontSize: 12, color: '#888' }}>最小 {Math.min(...workDaysList)} / 最大 {Math.max(...workDaysList)}</div>
              </Col>
              <Col span={8}>
                <Statistic title="労働時間（平均）" value={avg(hoursList).toFixed(1)} suffix="h" />
                <div style={{ fontSize: 12, color: '#888' }}>最小 {Math.min(...hoursList).toFixed(1)} / 最大 {Math.max(...hoursList).toFixed(1)}</div>
              </Col>
              <Col span={8}>
                <Statistic title="均衡度（標準偏差）" value={stddev(workDaysList).toFixed(2)} suffix="日" />
                <div style={{ fontSize: 12, color: '#888' }}>小さいほど公平</div>
              </Col>
            </Row>
          </Card>
        )
      })()}

      {violations.length > 0 && (
        <Card title={`違反レポート（${violations.length}件）`} style={{ marginBottom: 24 }}>
          <Collapse
            defaultActiveKey={Object.keys(groupedViolations)}
            items={Object.entries(groupedViolations).map(([group, items]) => {
              const info = GROUP_LABELS[group] || { text: group, color: 'default' }
              return {
                key: group,
                label: <span><Tag color={info.color}>{info.text}</Tag> {items.length}件</span>,
                children: (
                  <Table
                    dataSource={items.map((v, i) => ({ ...v, key: i }))}
                    columns={violationColumns}
                    size="small"
                    pagination={false}
                    expandable={{
                      expandedRowRender: (record: Violation) => renderViolationDetail(record),
                      rowExpandable: (record: Violation) =>
                        (record.contributing_factors?.length ?? 0) > 0 ||
                        (record.suggestions?.length ?? 0) > 0,
                    }}
                  />
                ),
              }
            })}
          />
        </Card>
      )}

      {result.warnings && result.warnings.length > 0 && (
        <Card title={`警告（${result.warnings.length}件）`}>
          <List
            dataSource={result.warnings}
            renderItem={(w) => (
              <List.Item>
                <Tag color={w.severity === 'error' ? 'red' : w.severity === 'warning' ? 'orange' : 'blue'}>
                  {w.severity}
                </Tag>
                {resolveIds(w.message)}
              </List.Item>
            )}
          />
        </Card>
      )}

      <Modal
        title="Excel取込確認"
        open={importModalOpen}
        onOk={handleImportExecute}
        onCancel={() => { setImportModalOpen(false); setImportFile(null); setImportPreview(null) }}
        okText="変更を反映"
        confirmLoading={importing}
        width={700}
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
            {importPreview.changes.length === 0 ? (
              <Alert type="info" message="変更はありません" />
            ) : (
              <>
                <Alert type="info" message={`${importPreview.changes.length} 件の変更を検出しました`} style={{ marginBottom: 16 }} />
                <Table
                  dataSource={importPreview.changes.map((c, i) => ({ ...c, key: i }))}
                  columns={[
                    { title: 'メンバー', dataIndex: 'member_name', key: 'member' },
                    { title: '日付', dataIndex: 'date_label', key: 'date' },
                    {
                      title: '変更前',
                      key: 'before',
                      render: (_: any, r: any) => <Tag color="red">{r.before.pattern_name}</Tag>,
                    },
                    {
                      title: '変更後',
                      key: 'after',
                      render: (_: any, r: any) => <Tag color="green">{r.after.pattern_name}</Tag>,
                    },
                  ]}
                  size="small"
                  pagination={importPreview.changes.length > 10 ? { pageSize: 10 } : false}
                />
              </>
            )}
          </>
        )}
      </Modal>
    </>
  )
}
