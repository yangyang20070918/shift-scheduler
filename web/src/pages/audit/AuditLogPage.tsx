import { useState, useEffect, useCallback } from 'react'
import { Table, Card, Select, DatePicker, Space, Tag, Row, Col, Statistic, Typography } from 'antd'
import {
  FileTextOutlined,
  LoginOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ThunderboltOutlined,
  ExportOutlined,
  UserAddOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { listAuditLogs, getAuditStats, type AuditLogItem, type AuditStatsResponse } from '../../api/audit-logs'

const { RangePicker } = DatePicker

const ACTION_CONFIG: Record<string, { color: string; label: string; icon: React.ReactNode }> = {
  LOGIN: { color: 'blue', label: 'ログイン', icon: <LoginOutlined /> },
  REGISTER: { color: 'cyan', label: '登録', icon: <UserAddOutlined /> },
  CREATE: { color: 'green', label: '作成', icon: <PlusOutlined /> },
  UPDATE: { color: 'orange', label: '更新', icon: <EditOutlined /> },
  DELETE: { color: 'red', label: '削除', icon: <DeleteOutlined /> },
  GENERATE: { color: 'purple', label: '生成', icon: <ThunderboltOutlined /> },
  EXPORT: { color: 'geekblue', label: '出力', icon: <ExportOutlined /> },
}

const RESOURCE_LABELS: Record<string, string> = {
  session: 'セッション',
  user: 'ユーザー',
  member: 'メンバー',
  pattern: 'パターン',
  schedule: 'スケジュール',
  demand: '需要',
  group: 'グループ',
  constraint: '制約',
}

export default function AuditLogPage() {
  const [logs, setLogs] = useState<AuditLogItem[]>([])
  const [total, setTotal] = useState(0)
  const [stats, setStats] = useState<AuditStatsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [filterAction, setFilterAction] = useState<string | undefined>()
  const [filterResource, setFilterResource] = useState<string | undefined>()
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null] | null>(null)
  const pageSize = 20

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string | number | undefined> = {
        offset: (page - 1) * pageSize,
        limit: pageSize,
        action: filterAction,
        resource_type: filterResource,
        date_from: dateRange?.[0]?.format('YYYY-MM-DD'),
        date_to: dateRange?.[1]?.format('YYYY-MM-DD'),
      }
      const [logRes, statsRes] = await Promise.all([
        listAuditLogs(params),
        getAuditStats({
          date_from: dateRange?.[0]?.format('YYYY-MM-DD'),
          date_to: dateRange?.[1]?.format('YYYY-MM-DD'),
        }),
      ])
      setLogs(logRes.items)
      setTotal(logRes.total)
      setStats(statsRes)
    } finally {
      setLoading(false)
    }
  }, [page, filterAction, filterResource, dateRange])

  useEffect(() => { load() }, [load])

  const columns = [
    {
      title: '日時',
      dataIndex: 'timestamp',
      width: 160,
      render: (v: string) => v ? dayjs(v).format('YYYY/MM/DD HH:mm:ss') : '',
    },
    {
      title: '操作',
      dataIndex: 'action',
      width: 100,
      render: (v: string) => {
        const cfg = ACTION_CONFIG[v] || { color: 'default', label: v, icon: null }
        return <Tag color={cfg.color} icon={cfg.icon}>{cfg.label}</Tag>
      },
    },
    {
      title: '対象',
      dataIndex: 'resource_type',
      width: 120,
      render: (v: string) => RESOURCE_LABELS[v] || v,
    },
    {
      title: 'ユーザー',
      dataIndex: 'user_email',
      width: 180,
      render: (v: string | null) => v || <Typography.Text type="secondary">system</Typography.Text>,
    },
    {
      title: '詳細',
      dataIndex: 'detail',
      render: (v: Record<string, unknown> | null) => {
        if (!v) return '-'
        return Object.entries(v)
          .map(([k, val]) => `${k}: ${val}`)
          .join(', ')
      },
    },
    {
      title: 'IP',
      dataIndex: 'ip_address',
      width: 130,
      responsive: ['lg' as const],
    },
  ]

  return (
    <div>
      <Typography.Title level={4} style={{ marginBottom: 16 }}>
        <FileTextOutlined /> 操作ログ
      </Typography.Title>

      {stats && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col xs={12} sm={6}>
            <Card size="small">
              <Statistic title="総件数" value={stats.total} />
            </Card>
          </Col>
          {stats.by_action.slice(0, 3).map(s => {
            const cfg = ACTION_CONFIG[s.key] || { label: s.key }
            return (
              <Col xs={12} sm={6} key={s.key}>
                <Card size="small">
                  <Statistic title={cfg.label} value={s.count} />
                </Card>
              </Col>
            )
          })}
        </Row>
      )}

      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Select
            placeholder="操作"
            allowClear
            style={{ width: 140 }}
            value={filterAction}
            onChange={v => { setFilterAction(v); setPage(1) }}
            options={Object.entries(ACTION_CONFIG).map(([k, v]) => ({ value: k, label: v.label }))}
          />
          <Select
            placeholder="対象"
            allowClear
            style={{ width: 140 }}
            value={filterResource}
            onChange={v => { setFilterResource(v); setPage(1) }}
            options={Object.entries(RESOURCE_LABELS).map(([k, v]) => ({ value: k, label: v }))}
          />
          <RangePicker
            value={dateRange as [dayjs.Dayjs, dayjs.Dayjs] | null}
            onChange={v => { setDateRange(v); setPage(1) }}
          />
        </Space>
      </Card>

      <Table
        dataSource={logs}
        columns={columns}
        rowKey="id"
        loading={loading}
        size="small"
        pagination={{
          current: page,
          pageSize,
          total,
          onChange: setPage,
          showTotal: t => `全 ${t} 件`,
          showSizeChanger: false,
        }}
        scroll={{ x: 800 }}
      />
    </div>
  )
}
