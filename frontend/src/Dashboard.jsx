import { useEffect, useState } from 'react'
import { djangoApi } from './api'
import './Dashboard.css'

function Dashboard({ onLogout }) {
  const [cards, setCards] = useState([])
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

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
        return
      }

      try {
        setLoading(true)
        setError('')

        const [cardsResponse, transactionsResponse] = await Promise.all([
          djangoApi.get('/cards/', {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }),
          djangoApi.get('/transactions/', {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }),
        ])

        setCards(cardsResponse.data)
        setTransactions(transactionsResponse.data)
      } catch (err) {
        console.error(err)

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

  const successfulTransactions = transactions.filter(
    (transaction) => transaction.status === 'SUCCESS'
  )

  const totalSpent = successfulTransactions.reduce(
    (total, transaction) => total + Number(transaction.amount || 0),
    0
  )

  return (
    <div className="dashboard-page">

      {/* HEADER */}
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
          <div className="secure-badge">
            🔒 Secure
          </div>

          <button
            className="logout-button"
            onClick={handleLogout}
          >
            Logout
          </button>
        </div>

      </header>

      {/* MAIN */}
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
            <span>ACCOUNT STATUS</span>
            <strong>● Active</strong>
          </div>

        </section>

        {/* ERROR */}
        {error && (
          <div className="dashboard-error">
            {error}
          </div>
        )}

        {/* STATS */}
        <section className="dashboard-stats">

          <div className="stat-card">
            <div className="stat-icon">💳</div>
            <div>
              <span>Total Cards</span>
              <strong>{cards.length}</strong>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">↔</div>
            <div>
              <span>Transactions</span>
              <strong>{transactions.length}</strong>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">✓</div>
            <div>
              <span>Successful</span>
              <strong>{successfulTransactions.length}</strong>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">₹</div>
            <div>
              <span>Total Spent</span>
              <strong>
                ₹{totalSpent.toFixed(2)}
              </strong>
            </div>
          </div>

        </section>

        {/* CONTENT GRID */}
        <section className="dashboard-grid">

          {/* CARDS */}
          <div className="dashboard-panel">

            <div className="panel-header">
              <div>
                <span className="panel-label">
                  PAYMENT METHODS
                </span>
                <h3>My Cards</h3>
              </div>

              <button className="panel-action">
                + Add Card
              </button>
            </div>

            {loading ? (
              <div className="empty-state">
                Loading cards...
              </div>
            ) : cards.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">💳</div>
                <strong>No cards added yet</strong>
                <p>Add your first card to start making payments.</p>
              </div>
            ) : (
              <div className="cards-list">

                {cards.map((card) => (
                  <div
                    className="mini-card"
                    key={card.id}
                  >
                    <div className="mini-card-top">
                      <strong>CARDPAY</strong>
                      <span>{card.card_type}</span>
                    </div>

                    <div className="mini-card-number">
                      {card.masked_card_number ||
                        `**** **** **** ${card.last4}`}
                    </div>

                    <div className="mini-card-bottom">
                      <div>
                        <small>CARD HOLDER</small>
                        <strong>
                          {card.card_holder_name}
                        </strong>
                      </div>

                      <div>
                        <small>EXPIRY</small>
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

            <h3>Make a Payment</h3>

            <p>
              Securely make a payment using one of your saved cards.
            </p>

            <button className="payment-button">
              Make Payment
              <span>→</span>
            </button>

            <div className="payment-security">
              <span>🔐</span>
              <div>
                <strong>Secure Payment</strong>
                <p>
                  Your card number and CVV are never stored.
                </p>
              </div>
            </div>

          </div>

        </section>

        {/* TRANSACTIONS */}
        <section className="dashboard-panel transactions-panel">

          <div className="panel-header">

            <div>
              <span className="panel-label">
                PAYMENT ACTIVITY
              </span>

              <h3>Recent Transactions</h3>
            </div>

            <button className="panel-action">
              View All
            </button>

          </div>

          {loading ? (
            <div className="empty-state">
              Loading transactions...
            </div>
          ) : transactions.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">↔</div>
              <strong>No transactions yet</strong>
              <p>Your payment activity will appear here.</p>
            </div>
          ) : (
            <div className="transactions-table">

              <div className="transaction-row transaction-heading">
                <span>Transaction</span>
                <span>Amount</span>
                <span>Status</span>
                <span>Date</span>
              </div>

              {transactions.slice(0, 5).map((transaction) => (
                <div
                  className="transaction-row"
                  key={transaction.id}
                >
                  <div className="transaction-name">
                    <div className="transaction-icon">
                      ₹
                    </div>

                    <div>
                      <strong>
                        Payment #{transaction.id}
                      </strong>

                      <small>
                        {transaction.description ||
                          'Card payment'}
                      </small>
                    </div>
                  </div>

                  <strong>
                    ₹{Number(transaction.amount).toFixed(2)}
                  </strong>

                  <span
                    className={`status-badge status-${transaction.status.toLowerCase()}`}
                  >
                    {transaction.status}
                  </span>

                  <span className="transaction-date">
                    {new Date(
                      transaction.created_at
                    ).toLocaleDateString()}
                  </span>

                </div>
              ))}

            </div>
          )}

        </section>

      </main>

      {/* FOOTER */}
      <footer className="dashboard-footer">
        <span>© 2026 CardPay Financial Platform</span>
        <span>256-bit Encryption • Secure Payments</span>
      </footer>

    </div>
  )
}

export default Dashboard