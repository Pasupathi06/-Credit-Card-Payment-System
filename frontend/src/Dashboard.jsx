import { useEffect, useState } from 'react'
import { djangoApi, fastApi } from './api'
import { useTheme } from './ThemeContext'
import './Dashboard.css'

function Dashboard({ onLogout }) {
  const [cards, setCards] = useState([])
  const [transactions, setTransactions] = useState([])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const { theme, toggleTheme } = useTheme()

  const getToken = () => {
    return (
      localStorage.getItem('access_token') ||
      sessionStorage.getItem('access_token')
    )
  }

  useEffect(() => {
    const loadDashboard = async () => {
      const token = getToken()

      if (!token) {
        setError('Session expired. Please login again.')
        setLoading(false)
        return
      }

      try {
        setLoading(true)
        setError('')

        const authConfig = {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }

        const [
          cardsResponse,
          transactionsResponse,
          summaryResponse,
        ] = await Promise.all([
          djangoApi.get('/cards/', authConfig),
          djangoApi.get('/transactions/', authConfig),
          fastApi.get('/dashboard/summary', authConfig),
        ])

        setCards(cardsResponse.data)
        setTransactions(transactionsResponse.data)
        setSummary(summaryResponse.data)
      } catch (err) {
        console.error('Dashboard loading error:', err)

        if (err.response?.status === 401) {
          setError('Session expired. Please login again.')
        } else {
          setError('Unable to load dashboard data.')
        }
      } finally {
        setLoading(false)
      }
    }

    loadDashboard()
  }, [])

  const handleLogout = async () => {
    const refreshToken =
      localStorage.getItem('refresh_token') ||
      sessionStorage.getItem('refresh_token')

    const accessToken =
      localStorage.getItem('access_token') ||
      sessionStorage.getItem('access_token')

    try {
      if (refreshToken && accessToken) {
        await djangoApi.post(
          '/auth/logout/',
          {
            refresh: refreshToken,
          },
          {
            headers: {
              Authorization: `Bearer ${accessToken}`,
            },
          }
        )
      }
    } catch (err) {
      console.error('Logout error:', err)
    } finally {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      sessionStorage.removeItem('access_token')
      sessionStorage.removeItem('refresh_token')

      onLogout()
    }
  }

  const formatAmount = (amount) => {
    return `₹${Number(amount || 0).toFixed(2)}`
  }

  const formatDate = (date) => {
    if (!date) return '-'

    const parsedDate = new Date(date)

    if (Number.isNaN(parsedDate.getTime())) {
      return '-'
    }

    return parsedDate.toLocaleDateString()
  }

  return (
    <div className="dashboard-page">

      {/* ================= HEADER ================= */}

      <header className="dashboard-header">

        <div className="dashboard-brand">

          <div className="dashboard-logo">
            ✦
          </div>

          <div>
            <h1>CardPay</h1>
            <span>FINANCIAL PLATFORM</span>
          </div>

        </div>

        <div className="dashboard-header-right">

          {/* THEME TOGGLE */}

          <button
            type="button"
            className="theme-toggle"
            onClick={toggleTheme}
            aria-label={
              theme === 'dark'
                ? 'Switch to light mode'
                : 'Switch to dark mode'
            }
            title={
              theme === 'dark'
                ? 'Switch to light mode'
                : 'Switch to dark mode'
            }
          >

            <span className="theme-toggle-icon">
              {theme === 'dark' ? '☀️' : '🌙'}
            </span>

            <span className="theme-toggle-text">
              {theme === 'dark' ? 'Light' : 'Dark'}
            </span>

          </button>

          {/* SECURITY */}

          <div className="secure-badge">
            🔒 Secure
          </div>

          {/* LOGOUT */}

          <button
            type="button"
            className="logout-button"
            onClick={handleLogout}
          >
            Logout
          </button>

        </div>

      </header>

      {/* ================= MAIN ================= */}

      <main className="dashboard-main">

        {/* WELCOME */}

        <section className="dashboard-welcome">

          <div>

            <span className="dashboard-eyebrow">
              SECURE DIGITAL PAYMENTS
            </span>

            <h2>
              Welcome back, Pasupathi 👋
            </h2>

            <p>
              Manage your cards, payments and transactions from one place.
            </p>

          </div>

          <div className="dashboard-date">

            <span>
              ACCOUNT STATUS
            </span>

            <strong>
              ● Active
            </strong>

          </div>

        </section>

        {/* ERROR */}

        {error && (
          <div className="dashboard-error">
            {error}
          </div>
        )}

        {/* ================= STATS ================= */}

        <section className="dashboard-stats">

          <div className="stat-card">

            <div className="stat-icon">
              ₹
            </div>

            <div>
              <span>Total Spent</span>

              {loading ? (
                <div className="stat-skeleton" />
              ) : (
                <strong>
                  {formatAmount(summary?.total_amount_spent)}
                </strong>
              )}

            </div>

          </div>

          <div className="stat-card">

            <div className="stat-icon">
              💳
            </div>

            <div>
              <span>Available Credit</span>

              {loading ? (
                <div className="stat-skeleton" />
              ) : (
                <strong>
                  {summary?.available_credit_limit !== null &&
                  summary?.available_credit_limit !== undefined
                    ? formatAmount(summary.available_credit_limit)
                    : 'Not available'}
                </strong>
              )}

            </div>

          </div>

          <div className="stat-card">

            <div className="stat-icon">
              ↔
            </div>

            <div>
              <span>Total Transactions</span>

              {loading ? (
                <div className="stat-skeleton" />
              ) : (
                <strong>
                  {summary?.total_transactions ?? 0}
                </strong>
              )}

            </div>

          </div>

          <div className="stat-card">

            <div className="stat-icon">
              📅
            </div>

            <div>
              <span>This Month Spending</span>

              {loading ? (
                <div className="stat-skeleton" />
              ) : (
                <strong>
                  {formatAmount(summary?.current_month_spending)}
                </strong>
              )}

            </div>

          </div>

        </section>

        {/* ================= CONTENT GRID ================= */}

        <section className="dashboard-grid">

          {/* MY CARDS */}

          <div className="dashboard-panel">

            <div className="panel-header">

              <div>

                <span className="panel-label">
                  PAYMENT METHODS
                </span>

                <h3>
                  My Cards
                </h3>

              </div>

              <button
                type="button"
                className="panel-action"
              >
                + Add Card
              </button>

            </div>

            {loading ? (

              <div className="empty-state">
                Loading cards...
              </div>

            ) : cards.length === 0 ? (

              <div className="empty-state">

                <div className="empty-icon">
                  💳
                </div>

                <strong>
                  No cards added yet
                </strong>

                <p>
                  Add your first card to start making payments.
                </p>

              </div>

            ) : (

              <div className="cards-list">

                {cards.map((card) => (

                  <div
                    className="mini-card"
                    key={card.id}
                  >

                    <div className="mini-card-top">

                      <strong>
                        CARDPAY
                      </strong>

                      <span>
                        {card.card_type}
                      </span>

                    </div>

                    <div className="mini-card-number">
                      {card.masked_card_number ||
                        `**** **** **** ${card.last4}`}
                    </div>

                    <div className="mini-card-bottom">

                      <div>

                        <small>
                          CARD HOLDER
                        </small>

                        <strong>
                          {card.card_holder_name}
                        </strong>

                      </div>

                      <div>

                        <small>
                          EXPIRY
                        </small>

                        <strong>
                          {String(card.expiry_month).padStart(2, '0')}/
                          {card.expiry_year}
                        </strong>

                      </div>

                    </div>

                  </div>

                ))}

              </div>

            )}

          </div>

          {/* QUICK PAYMENT */}

          <div className="dashboard-panel payment-panel">

            <span className="panel-label">
              QUICK ACTION
            </span>

            <h3>
              Make a Payment
            </h3>

            <p>
              Securely make a payment using one of your saved cards.
            </p>

            <button
              type="button"
              className="payment-button"
            >
              Make Payment
              <span>→</span>
            </button>

            <div className="payment-security">

              <span>
                🔐
              </span>

              <div>

                <strong>
                  Secure Payment
                </strong>

                <p>
                  Your card number and CVV are never stored.
                </p>

              </div>

            </div>

          </div>

        </section>

        {/* ================= TRANSACTIONS ================= */}

        <section className="dashboard-panel transactions-panel">

          <div className="panel-header">

            <div>

              <span className="panel-label">
                PAYMENT ACTIVITY
              </span>

              <h3>
                Last 5 Transactions
              </h3>

            </div>

            <button
              type="button"
              className="panel-action"
            >
              View All
            </button>

          </div>

          {loading ? (

            <div className="empty-state">

              <div className="transaction-loading">
                Loading transactions...
              </div>

            </div>

          ) : summary?.last_5_transactions?.length === 0 ? (

            <div className="empty-state">

              <div className="empty-icon">
                ↔
              </div>

              <strong>
                No transactions yet
              </strong>

              <p>
                Your payment activity will appear here.
              </p>

            </div>

          ) : (

            <div className="transactions-table">

              <div className="transaction-row transaction-heading">

                <span>Transaction</span>
                <span>Amount</span>
                <span>Status</span>
                <span>Date</span>

              </div>

              {summary?.last_5_transactions?.map(
                (transaction, index) => (

                  <div
                    className="transaction-row"
                    key={`${transaction.date}-${index}`}
                  >

                    <div className="transaction-name">

                      <div className="transaction-icon">
                        ₹
                      </div>

                      <div>

                        <strong>
                          {transaction.masked_card_number || '****'}
                        </strong>

                        <small>
                          Card payment
                        </small>

                      </div>

                    </div>

                    <strong>
                      {formatAmount(transaction.amount)}
                    </strong>

                    <span
                      className={`status-badge status-${String(
                        transaction.status || ''
                      ).toLowerCase()}`}
                    >
                      {transaction.status}
                    </span>

                    <span className="transaction-date">
                      {formatDate(transaction.date)}
                    </span>

                  </div>

                )
              )}

            </div>

          )}

        </section>

      </main>

      {/* ================= FOOTER ================= */}

      <footer className="dashboard-footer">

        <span>
          © 2026 CardPay Financial Platform
        </span>

        <span>
          256-bit Encryption • Secure Payments
        </span>

      </footer>

    </div>
  )
}

export default Dashboard