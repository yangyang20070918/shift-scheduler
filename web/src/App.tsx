import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider, App as AntApp } from 'antd'
import { AuthContext } from './store/auth'
import { getMe, type User } from './api/auth'
import AppLayout from './components/AppLayout'
import LoginPage from './pages/auth/LoginPage'
import MembersPage from './pages/members/MembersPage'
import PatternsPage from './pages/patterns/PatternsPage'
import PatternRulesPage from './pages/patterns/PatternRulesPage'
import SchedulesPage from './pages/schedules/SchedulesPage'
import ScheduleResultPage from './pages/schedules/ScheduleResultPage'
import ScheduleDetailPage from './pages/schedules/ScheduleDetailPage'
import ConstraintsPage from './pages/constraints/ConstraintsPage'
import GroupsPage from './pages/groups/GroupsPage'
import PersonalPage from './pages/personal/PersonalPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('token')
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'))
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (token) {
      getMe()
        .then(setUser)
        .catch(() => {
          localStorage.removeItem('token')
          setToken(null)
        })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [token])

  function setAuth(t: string, u: User) {
    setToken(t)
    setUser(u)
  }

  function logout() {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
  }

  if (loading) return null

  return (
    <ConfigProvider>
      <AntApp>
        <AuthContext.Provider value={{ user, token, setAuth, logout }}>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/personal/:token" element={<PersonalPage />} />
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <AppLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<Navigate to="/schedules" replace />} />
                <Route path="members" element={<MembersPage />} />
                <Route path="patterns" element={<PatternsPage />} />
                <Route path="pattern-rules" element={<PatternRulesPage />} />
                <Route path="schedules" element={<SchedulesPage />} />
                <Route path="schedules/:id" element={<ScheduleDetailPage />} />
                <Route path="schedules/:id/result" element={<ScheduleResultPage />} />
                <Route path="constraints" element={<ConstraintsPage />} />
                <Route path="groups" element={<GroupsPage />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </AuthContext.Provider>
      </AntApp>
    </ConfigProvider>
  )
}
