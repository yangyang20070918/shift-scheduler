import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Card, Tag, Button, Calendar, Badge, Modal, Spin, Typography, message, List, Divider, Empty } from 'antd'
import { CheckCircleOutlined, CalendarOutlined, ScheduleOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'
import {
  getPersonalInfo,
  getRestRequest,
  updateRestRequest,
  submitRestRequest,
  getMySchedule,
  type PersonalInfo,
  type PersonalRestRequest,
  type MySchedule,
} from '../../api/personal'

export default function PersonalPage() {
  const { token } = useParams<{ token: string }>()
  const [info, setInfo] = useState<PersonalInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeScheduleId, setActiveScheduleId] = useState<string | null>(null)
  const [restData, setRestData] = useState<PersonalRestRequest | null>(null)
  const [selectedDates, setSelectedDates] = useState<string[]>([])
  const [saving, setSaving] = useState(false)
  const [mySchedule, setMySchedule] = useState<MySchedule | null>(null)
  const [scheduleModalOpen, setScheduleModalOpen] = useState(false)
  const [viewScheduleId, setViewScheduleId] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return
    setLoading(true)
    getPersonalInfo(token)
      .then(setInfo)
      .catch(() => message.error('認証に失敗しました。リンクを確認してください。'))
      .finally(() => setLoading(false))
  }, [token])

  async function openRestRequest(scheduleId: string) {
    if (!token) return
    setActiveScheduleId(scheduleId)
    const data = await getRestRequest(token, scheduleId)
    setRestData(data)
    setSelectedDates(data.request.requested_dates)
  }

  async function handleDateSelect(date: Dayjs) {
    if (!restData || restData.request.status === 'submitted') return

    const dateStr = date.format('YYYY-MM-DD')
    const startDate = dayjs(restData.start_date)
    const endDate = startDate.add(restData.num_days - 1, 'day')

    if (date.isBefore(startDate, 'day') || date.isAfter(endDate, 'day')) return

    let newDates: string[]
    if (selectedDates.includes(dateStr)) {
      newDates = selectedDates.filter((d) => d !== dateStr)
    } else {
      if (selectedDates.length >= restData.rest_request_max_days) {
        message.warning(`最大${restData.rest_request_max_days}日まで選択できます`)
        return
      }
      newDates = [...selectedDates, dateStr].sort()
    }

    setSelectedDates(newDates)

    setSaving(true)
    try {
      await updateRestRequest(token!, activeScheduleId!, newDates)
    } catch {
      message.error('保存に失敗しました')
    } finally {
      setSaving(false)
    }
  }

  async function handleSubmit() {
    if (!token || !activeScheduleId) return
    try {
      await submitRestRequest(token, activeScheduleId)
      message.success('提出しました。変更はできません。')
      openRestRequest(activeScheduleId)
      getPersonalInfo(token).then(setInfo)
    } catch {
      message.error('提出に失敗しました')
    }
  }

  async function handleViewSchedule(scheduleId: string) {
    if (!token) return
    setViewScheduleId(scheduleId)
    try {
      const data = await getMySchedule(token, scheduleId)
      setMySchedule(data)
      setScheduleModalOpen(true)
    } catch {
      message.error('スケジュールの読み込みに失敗しました')
    }
  }

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />

  if (!info) {
    return (
      <div style={{ maxWidth: 480, margin: '40px auto', padding: '0 16px' }}>
        <Card>
          <Empty description="無効なリンクです。管理者にお問い合わせください。" />
        </Card>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 480, margin: '0 auto', padding: '16px', minHeight: '100vh', background: '#f5f5f5' }}>
      <Card style={{ marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>
          {info.member_name} さん
        </Typography.Title>
        <Typography.Text type="secondary">シフトスケジューラー</Typography.Text>
      </Card>

      {info.schedules.length === 0 && (
        <Card>
          <Empty description="現在、対象のスケジュールはありません" />
        </Card>
      )}

      {info.schedules.map((sched) => (
        <Card
          key={sched.id}
          style={{ marginBottom: 12 }}
          title={sched.name || 'スケジュール'}
          extra={
            sched.status === 'requesting' ? (
              <Tag color="processing">受付中</Tag>
            ) : sched.status === 'completed' ? (
              <Tag color="success">確定</Tag>
            ) : (
              <Tag>{sched.status}</Tag>
            )
          }
        >
          <Typography.Text type="secondary">
            {sched.start_date} 〜 {sched.num_days}日間
          </Typography.Text>

          {sched.status === 'requesting' && (
            <div style={{ marginTop: 12 }}>
              {sched.my_request_status === 'submitted' ? (
                <div>
                  <Tag color="green" icon={<CheckCircleOutlined />}>提出済み</Tag>
                  <div style={{ marginTop: 8 }}>
                    希望日: {sched.my_requested_dates.length > 0 ? sched.my_requested_dates.join(', ') : 'なし'}
                  </div>
                </div>
              ) : (
                <Button
                  type="primary"
                  icon={<CalendarOutlined />}
                  onClick={() => openRestRequest(sched.id)}
                  block
                >
                  休み希望を選択
                </Button>
              )}
            </div>
          )}

          {sched.status === 'completed' && (
            <div style={{ marginTop: 12 }}>
              <Button
                icon={<ScheduleOutlined />}
                onClick={() => handleViewSchedule(sched.id)}
                block
              >
                マイスケジュールを見る
              </Button>
            </div>
          )}
        </Card>
      ))}

      <Modal
        title="休み希望日を選択"
        open={!!activeScheduleId && !!restData}
        onCancel={() => { setActiveScheduleId(null); setRestData(null) }}
        footer={
          restData?.request.status !== 'submitted' ? (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography.Text>
                {selectedDates.length} / {restData?.rest_request_max_days ?? 3} 日選択中
              </Typography.Text>
              <Button
                type="primary"
                icon={<CheckCircleOutlined />}
                onClick={handleSubmit}
                disabled={saving}
              >
                確定提出
              </Button>
            </div>
          ) : null
        }
        width="100%"
        style={{ top: 16, maxWidth: 480 }}
      >
        {restData && (
          <div>
            {restData.request.status === 'submitted' && (
              <Tag color="green" style={{ marginBottom: 12 }}>提出済み（変更不可）</Tag>
            )}

            {restData.rest_request_deadline && (
              <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
                締切日: {restData.rest_request_deadline}
              </Typography.Text>
            )}

            <Calendar
              fullscreen={false}
              value={dayjs(restData.start_date)}
              onSelect={handleDateSelect}
              cellRender={(date) => {
                const dateStr = date.format('YYYY-MM-DD')
                const startDate = dayjs(restData.start_date)
                const endDate = startDate.add(restData.num_days - 1, 'day')

                if (date.isBefore(startDate, 'day') || date.isAfter(endDate, 'day')) return null

                if (selectedDates.includes(dateStr)) {
                  return (
                    <div style={{
                      position: 'absolute',
                      inset: 0,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}>
                      <Badge status="success" />
                    </div>
                  )
                }
                return null
              }}
            />

            {selectedDates.length > 0 && (
              <div style={{ marginTop: 8 }}>
                <Typography.Text strong>選択中の日付:</Typography.Text>
                <div style={{ marginTop: 4 }}>
                  {selectedDates.map((d) => (
                    <Tag key={d} color="blue" style={{ marginBottom: 4 }}>
                      {d}
                    </Tag>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>

      <Modal
        title="マイスケジュール"
        open={scheduleModalOpen}
        onCancel={() => { setScheduleModalOpen(false); setMySchedule(null) }}
        footer={null}
        width="100%"
        style={{ top: 16, maxWidth: 480 }}
      >
        {mySchedule && mySchedule.assignments.length > 0 ? (
          <List
            size="small"
            dataSource={mySchedule.assignments}
            renderItem={(a) => (
              <List.Item>
                <span style={{ width: 100 }}>{a.date}</span>
                <Tag color={a.is_rest ? 'green' : 'blue'}>
                  {a.is_rest ? '休み' : (a.pattern_id || '出勤')}
                </Tag>
              </List.Item>
            )}
          />
        ) : (
          <Empty description="スケジュールはまだ確定していません" />
        )}
      </Modal>
    </div>
  )
}
