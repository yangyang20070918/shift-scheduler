import { useEffect, useState } from 'react'
import { Button, Card, Table, Tag, Statistic, Row, Col, Alert, Spin, Progress, Collapse, List, Typography, Space, message } from 'antd'
import { DownloadOutlined } from '@ant-design/icons'
import { useParams, useNavigate } from 'react-router-dom'
import { getScheduleResult, exportExcel, type ScheduleResult, type Assignment, type Violation } from '../../api/schedules'
import { listMembers } from '../../api/members'
import { listPatterns } from '../../api/patterns'

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
  const [patterns, setPatterns] = useState<Record<string, { name: string; color: string }>>({})

  useEffect(() => {
    async function load() {
      if (!id) return
      const [r, mList, pList] = await Promise.all([
        getScheduleResult(id),
        listMembers(),
        listPatterns(),
      ])
      setResult(r)
      setMembers(Object.fromEntries(mList.map((m) => [m.id, m.name])))
      setPatterns(Object.fromEntries(pList.map((p) => [p.id, { name: p.name, color: p.color_code }])))
      setLoading(false)
    }
    load()
  }, [id])

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
    ...dates.map((d) => ({
      title: d.slice(5),
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
    })),
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
      width: 80,
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
            ].map(({ label, key, color }) => (
              <Col span={6} key={key}>
                <div style={{ textAlign: 'center', marginBottom: 8 }}>
                  <div style={{ fontWeight: 500, marginBottom: 4 }}>{label}</div>
                  <Progress
                    type="circle"
                    size={80}
                    percent={Math.max(0, 100 - ((result.score_breakdown as any)?.[key] ?? 0))}
                    strokeColor={color}
                    format={() => `${(result.score_breakdown as any)?.[key] ?? 0}`}
                  />
                  <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>ペナルティ</div>
                </div>
              </Col>
            ))}
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
                {w.message}
              </List.Item>
            )}
          />
        </Card>
      )}
    </>
  )
}
