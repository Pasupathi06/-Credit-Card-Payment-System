import { useEffect, useState } from 'react'
import { useTheme } from './ThemeContext'
import './App.css'
import { djangoApi, fastApi } from './api'

function App() {
  const { theme, toggleTheme } = useTheme()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [rememberMe, setRememberMe] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [userInfo, setUserInfo] = useState(null)

  const [cards, setCards] = useState([])
  const [transactions, setTransactions] = useState([])

  const [isAdmin, setIsAdmin] = useState(false)
  const [adminSummary, setAdminSummary] = useState(null)
  const [adminUsers, setAdminUsers] = useState([])
  const [adminCards, setAdminCards] = useState([])
  const [adminTransactions, setAdminTransactions] = useState([])
  const [adminLoading, setAdminLoading] = useState(false)
  const [adminError, setAdminError] = useState('')
  const [csvLoading, setCsvLoading] = useState(false)

  const [showAddCard, setShowAddCard] = useState(false)
  const [cardLoading, setCardLoading] = useState(false)
  const [cardMessage, setCardMessage] = useState('')

  const [paymentLoading, setPaymentLoading] = useState(false)
  const [paymentMessage, setPaymentMessage] = useState('')

  const [cardForm, setCardForm] = useState({
    card_holder_name: '',
    card_number: '',
    card_type: 'VISA',
    expiry_month: '',
    expiry_year: '',
  })

  const [paymentForm, setPaymentForm] = useState({
    card_id: '',
    amount: '',
    description: '',
  })

  // --------------------------------------------------
  // GET STORED TOKEN
  // --------------------------------------------------

  const getAccessToken = () => {
    return (
      localStorage.getItem('access_token') ||
      sessionStorage.getItem('access_token')
    )
  }

  // --------------------------------------------------
  // DECODE JWT
  // --------------------------------------------------

  const decodeJwt = (token) => {
    try {
      const payload = token.split('.')[1]
      const decoded = JSON.parse(
        atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
      )

      return decoded
    } catch {
      return null
    }
  }

  // --------------------------------------------------
  // LOGIN
  // --------------------------------------------------

  const handleLogin = async (event) => {
    event.preventDefault()

    setError('')

    if (!username.trim() || !password) {
      setError('Please enter your username and password.')
      return
    }

    try {
      setLoading(true)

      const response = await djangoApi.post('/auth/login/', {
        username: username.trim(),
        password: password,
      })

      const { access, refresh } = response.data

      if (rememberMe) {
        localStorage.setItem('access_token', access)
        localStorage.setItem('refresh_token', refresh)
      } else {
        sessionStorage.setItem('access_token', access)
        sessionStorage.setItem('refresh_token', refresh)
      }

      const decodedUser = decodeJwt(access)

      setUserInfo({
        id: decodedUser?.user_id,
        username:
          decodedUser?.username ||
          username.trim(),
        email: decodedUser?.email || '',
      })

      setIsLoggedIn(true)

    } catch (err) {
      if (err.response?.data?.detail) {
        setError(err.response.data.detail)
      } else if (err.response?.status === 401) {
        setError('Invalid username or password.')
      } else if (err.response?.status === 400) {
        setError('Invalid login details.')
      } else {
        setError('Unable to connect to the server. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  // --------------------------------------------------
  // LOAD DASHBOARD DATA
  // --------------------------------------------------

  useEffect(() => {
    if (isLoggedIn) {
      loadDashboardData()
    }
  }, [isLoggedIn])

  const loadDashboardData = async () => {
    const token = getAccessToken()

    if (!token) {
      handleLogout()
      return
    }

    try {
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

      setCards(cardsResponse.data || [])
      setTransactions(transactionsResponse.data || [])

      // Check whether the logged-in user is an admin/staff user.
      // This keeps normal user accounts on the existing dashboard while
      // enabling the admin panel only for users allowed by Django.
      try {
        const adminUsersResponse = await djangoApi.get('/auth/admin/users/', {
          headers: { Authorization: `Bearer ${token}` },
        })
        const users = adminUsersResponse.data || []
        const currentAdmin = users.find(
          (user) => Number(user.id) === Number(userInfo?.id)
        )

        if (currentAdmin?.is_staff) {
          setIsAdmin(true)
          setAdminUsers(users)
          await loadAdminData(token)
        } else {
          setIsAdmin(false)
        }
      } catch (adminErr) {
        // 403 for a normal user is expected; do not break the user dashboard.
        setIsAdmin(false)
      }
    } catch (err) {
      console.error('Dashboard loading error:', err)

      if (err.response?.status === 401) {
        handleLogout()
      }
    }
  }

  const loadAdminData = async (token = getAccessToken()) => {
    if (!token) return

    setAdminLoading(true)
    setAdminError('')

    try {
      const headers = { Authorization: `Bearer ${token}` }
      const [summaryResponse, usersResponse, cardsResponse, transactionsResponse] =
        await Promise.all([
          djangoApi.get('/transactions/admin/dashboard/', { headers }),
          djangoApi.get('/auth/admin/users/', { headers }),
          djangoApi.get('/cards/admin/', { headers }),
          djangoApi.get('/transactions/admin/', { headers }),
        ])

      setAdminSummary(summaryResponse.data || null)
      setAdminUsers(usersResponse.data || [])
      setAdminCards(cardsResponse.data || [])
      setAdminTransactions(transactionsResponse.data || [])
    } catch (err) {
      console.error('Admin dashboard loading error:', err)
      setAdminError(
        err.response?.status === 403
          ? 'You do not have permission to view the admin dashboard.'
          : 'Unable to load admin dashboard data.'
      )
    } finally {
      setAdminLoading(false)
    }
  }

  const handleExportCsv = async () => {
    const token = getAccessToken()
    if (!token) return

    setCsvLoading(true)
    try {
      const response = await djangoApi.get('/transactions/admin/export-csv/', {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob',
      })

      const blob = new Blob([response.data], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'transactions.csv'
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error('CSV export error:', err)
      setAdminError('Unable to export transactions CSV.')
    } finally {
      setCsvLoading(false)
    }
  }

  // --------------------------------------------------
  // ADD CARD
  // --------------------------------------------------

  const handleAddCard = async (event) => {
    event.preventDefault()

    setCardLoading(true)
    setCardMessage('')

    const token = getAccessToken()

    try {
      await djangoApi.post(
        '/cards/',
        {
          card_holder_name: cardForm.card_holder_name,
          card_number: cardForm.card_number,
          card_type: cardForm.card_type,
          expiry_month: Number(cardForm.expiry_month),
          expiry_year: Number(cardForm.expiry_year),
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      )

      setCardMessage('Card added successfully.')

      setCardForm({
        card_holder_name: '',
        card_number: '',
        card_type: 'VISA',
        expiry_month: '',
        expiry_year: '',
      })

      setShowAddCard(false)

      await loadDashboardData()
    } catch (err) {
      console.error('Add card error:', err)

      if (err.response?.data) {
        const data = err.response.data

        const firstError =
          data.card_number?.[0] ||
          data.card_holder_name?.[0] ||
          data.expiry_month?.[0] ||
          data.expiry_year?.[0] ||
          data.detail

        setCardMessage(firstError || 'Unable to add card.')
      } else {
        setCardMessage('Unable to connect to the server.')
      }
    } finally {
      setCardLoading(false)
    }
  }

  // --------------------------------------------------
  // DELETE CARD
  // --------------------------------------------------

  const handleDeleteCard = async (cardId) => {
    const confirmDelete = window.confirm(
      'Are you sure you want to delete this card?'
    )

    if (!confirmDelete) {
      return
    }

    const token = getAccessToken()

    try {
      await djangoApi.delete(`/cards/${cardId}/`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      await loadDashboardData()
    } catch (err) {
      console.error('Delete card error:', err)
      alert('Unable to delete card.')
    }
  }

  // --------------------------------------------------
  // MAKE PAYMENT
  // --------------------------------------------------

  const handlePayment = async (event) => {
    event.preventDefault()

    setPaymentLoading(true)
    setPaymentMessage('')

    const token = getAccessToken()

    if (!paymentForm.card_id || !paymentForm.amount) {
      setPaymentMessage('Please select a card and enter amount.')
      setPaymentLoading(false)
      return
    }

    try {
      const response = await fastApi.post('/payments/', {
        user_id: userInfo?.id,
        card_id: Number(paymentForm.card_id),
        amount: Number(paymentForm.amount),
        description:
          paymentForm.description || 'Card payment',
      })

      const payment = response.data

      setPaymentMessage(
        `Payment #${payment.id} completed with status: ${payment.status}`
      )

      setPaymentForm({
        card_id: '',
        amount: '',
        description: '',
      })

      await loadDashboardData()
    } catch (err) {
      console.error('Payment error:', err)

      if (err.response?.data?.detail) {
        const detail = err.response.data.detail

        if (typeof detail === 'string') {
          setPaymentMessage(detail)
        } else {
          setPaymentMessage(
            detail.message || 'Payment processing failed.'
          )
        }
      } else {
        setPaymentMessage(
          'Unable to connect to the payment server.'
        )
      }
    } finally {
      setPaymentLoading(false)
    }
  }

  // --------------------------------------------------
  // LOGOUT
  // --------------------------------------------------

  const handleLogout = async () => {
    const refreshToken =
      localStorage.getItem('refresh_token') ||
      sessionStorage.getItem('refresh_token')

    const accessToken = getAccessToken()

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
      console.log('Logout API error:', err)
    }

    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')

    sessionStorage.removeItem('access_token')
    sessionStorage.removeItem('refresh_token')

    setIsLoggedIn(false)
    setUserInfo(null)
    setCards([])
    setTransactions([])
  }

  // --------------------------------------------------
  // LOGIN PAGE
  // --------------------------------------------------

  if (!isLoggedIn) {
    return (
      <div className="login-page">

        <div className="glow glow-one"></div>
        <div className="glow glow-two"></div>
        <div className="glow glow-three"></div>

        <main className="login-container">

          {/* LEFT SIDE */}

          <section className="brand-section">

            <div className="brand-top">

              <div className="brand-logo">
                <span>✦</span>
              </div>

              <div>
                <h1>CardPay</h1>
                <p>FINANCIAL PLATFORM</p>
              </div>

            </div>

            <div className="brand-content">

              <div className="eyebrow">
                <span className="status-dot"></span>
                SECURE DIGITAL PAYMENTS
              </div>

              <h2>
                Your money.
                <br />
                <span>Simply managed.</span>
              </h2>

              <p className="brand-description">
                A smarter way to manage your cards, make payments,
                and keep track of every transaction in one secure place.
              </p>

              <div className="credit-card">

                <div className="card-top">
                  <span className="card-brand">
                    CARDPAY
                  </span>

                  <span className="contactless">
                    )))
                  </span>
                </div>

                <div className="chip">
                  <div></div>
                  <div></div>
                  <div></div>
                </div>

                <div className="card-number">
                  4582&nbsp;&nbsp; ****&nbsp;&nbsp; ****&nbsp;&nbsp; 2418
                </div>

                <div className="card-bottom">

                  <div>
                    <small>CARD HOLDER</small>
                    <strong>PASUPATHI PANDI</strong>
                  </div>

                  <div>
                    <small>VALID THRU</small>
                    <strong>12/29</strong>
                  </div>

                  <div className="master-logo">
                    <span></span>
                    <span></span>
                  </div>

                </div>

              </div>

              <div className="trust-row">

                <div>
                  <strong>256-bit</strong>
                  <span>Encryption</span>
                </div>

                <div>
                  <strong>24/7</strong>
                  <span>Monitoring</span>
                </div>

                <div>
                  <strong>99.9%</strong>
                  <span>Reliability</span>
                </div>

              </div>

            </div>

          </section>

          {/* RIGHT SIDE */}

          <section className="login-section">

            <div className="login-box">

              <div className="mobile-brand">

                <div className="brand-logo">
                  <span>✦</span>
                </div>

                <h1>CardPay</h1>

              </div>

              <div className="login-header">

                <span className="welcome-label">
                  WELCOME BACK
                </span>

                <h2>
                  Sign in to your account
                </h2>

                <p>
                  Enter your details below to access your secure dashboard.
                </p>

              </div>

              <form onSubmit={handleLogin}>

                {/* USERNAME */}

                <div className="input-group">

                  <label>
                    Username
                  </label>

                  <div className="input-wrapper">

                    <span className="input-icon">
                      ✉
                    </span>

                    <input
                      type="text"
                      placeholder="Enter your username"
                      value={username}
                      onChange={(event) =>
                        setUsername(event.target.value)
                      }
                      autoComplete="username"
                    />

                  </div>

                </div>

                {/* PASSWORD */}

                <div className="input-group">

                  <div className="label-row">

                    <label>
                      Password
                    </label>

                    <button
                      type="button"
                      className="forgot-button"
                      onClick={() => {
                        setError(
                          'Password reset is not available yet.'
                        )
                      }}
                    >
                      Forgot password?
                    </button>

                  </div>

                  <div className="input-wrapper">

                    <span className="input-icon">
                      ●
                    </span>

                    <input
                      type={
                        showPassword
                          ? 'text'
                          : 'password'
                      }
                      placeholder="Enter your password"
                      value={password}
                      onChange={(event) =>
                        setPassword(event.target.value)
                      }
                      autoComplete="current-password"
                    />

                    <button
                      type="button"
                      className="eye-button"
                      onClick={() =>
                        setShowPassword(!showPassword)
                      }
                      aria-label="Show or hide password"
                    >
                      {showPassword ? '◉' : '○'}
                    </button>

                  </div>

                </div>

                {/* ERROR */}

                {error && (
                  <div className="login-error">
                    {error}
                  </div>
                )}

                {/* REMEMBER */}

                <div className="remember-row">

                  <label className="remember">

                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(event) =>
                        setRememberMe(
                          event.target.checked
                        )
                      }
                    />

                    <span>
                      Remember me
                    </span>

                  </label>

                  <span className="secure-text">
                    🔒 Secure login
                  </span>

                </div>

                {/* LOGIN */}

                <button
                  type="submit"
                  className="login-button"
                  disabled={loading}
                >

                  <span>
                    {loading
                      ? 'Signing in...'
                      : 'Sign in securely'}
                  </span>

                  <span className="arrow">
                    {loading
                      ? '...'
                      : '→'}
                  </span>

                </button>

              </form>

              <div className="divider">
                <span>OR</span>
              </div>

              <button
                type="button"
                className="demo-button"
                onClick={() => {
                  setError(
                    'Demo account is not configured yet.'
                  )
                }}
              >
                <span>◈</span>
                Continue with demo account
              </button>

              <p className="register-text">

                Don't have an account?

                <button
                  type="button"
                  onClick={() => {
                    setError(
                      'Registration page will be added next.'
                    )
                  }}
                >
                  Create an account
                </button>

              </p>

              <div className="login-footer">

                <span>Privacy</span>
                <span>•</span>
                <span>Terms</span>
                <span>•</span>
                <span>Security</span>

              </div>

            </div>

          </section>

        </main>

        <p className="copyright">
          © 2026 CardPay Financial Platform. All rights reserved.
        </p>

      </div>
    )
  }

  // --------------------------------------------------
  // DASHBOARD
  // --------------------------------------------------

  const successfulPayments = transactions.filter(
    (transaction) => transaction.status === 'SUCCESS'
  ).length

  const failedPayments = transactions.filter(
    (transaction) => transaction.status === 'FAILED'
  ).length

  const pendingPayments = transactions.filter(
    (transaction) => transaction.status === 'PENDING'
  ).length

  const totalAmount = transactions
    .filter((transaction) => transaction.status === 'SUCCESS')
    .reduce(
      (total, transaction) => total + Number(transaction.amount || 0),
      0
    )

  return (
    <div className="dashboard-page">
      <header className="dashboard-header">
        <div className="dashboard-brand">
          <div className="dashboard-logo">✦</div>
          <div>
            <div className="dashboard-brand-name">CardPay</div>
            <div className="dashboard-brand-subtitle">FINANCIAL PLATFORM</div>
          </div>
        </div>

        <div className="dashboard-header-right">
          <div className="dashboard-user">
            <span className="dashboard-user-label">Welcome back</span>
            <strong>{userInfo?.username || 'User'}</strong>
          </div>

          <button
            type="button"
            className={`theme-toggle ${
              theme === 'dark' ? 'dark-mode' : 'light-mode'
            }`}
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
              {theme === 'dark' ? '🌙' : '☀️'}
            </span>
            <span className="theme-toggle-text">
              {theme === 'dark' ? 'Dark' : 'Light'}
            </span>
          </button>

          <button
            type="button"
            className="dashboard-secure-badge"
            aria-label="Secure session active"
            title="Secure session active"
          >
            <span className="secure-badge-icon">🔒</span>
            <span>Secure</span>
          </button>

          <button
            type="button"
            onClick={handleLogout}
            className="dashboard-logout"
          >
            <span>↪</span>
            <span>Logout</span>
          </button>
        </div>
      </header>

      <main className="dashboard-main">
        <section className="dashboard-hero">
          <div>
            <div className="dashboard-eyebrow">
              <span className="dashboard-live-dot"></span>
              SECURE DASHBOARD
            </div>
            <h1>Hello, {userInfo?.username || 'User'} <span>👋</span></h1>
            <p>Manage your cards, make payments, and track your activity securely from one place.</p>
          </div>

          <div className="dashboard-hero-badge">
            <div className="hero-badge-icon">✓</div>
            <div>
              <strong>Account Protected</strong>
              <span>Secure session active</span>
            </div>
          </div>
        </section>

        <section className="summary-grid">
          <div className="summary-card summary-card-teal">
            <div className="summary-card-top">
              <span className="summary-label">Total Cards</span>
              <span className="summary-icon">▣</span>
            </div>
            <strong>{cards.length}</strong>
            <span className="summary-note">Saved payment cards</span>
          </div>

          <div className="summary-card summary-card-blue">
            <div className="summary-card-top">
              <span className="summary-label">Transactions</span>
              <span className="summary-icon">↗</span>
            </div>
            <strong>{transactions.length}</strong>
            <span className="summary-note">Total payment activity</span>
          </div>

          <div className="summary-card summary-card-green">
            <div className="summary-card-top">
              <span className="summary-label">Successful</span>
              <span className="summary-icon">✓</span>
            </div>
            <strong>{successfulPayments}</strong>
            <span className="summary-note">Completed payments</span>
          </div>

          <div className="summary-card summary-card-purple">
            <div className="summary-card-top">
              <span className="summary-label">Payment Volume</span>
              <span className="summary-icon">₹</span>
            </div>
            <strong>₹{totalAmount.toFixed(2)}</strong>
            <span className="summary-note">{failedPayments} failed · {pendingPayments} pending</span>
          </div>
        </section>

        <section className="dashboard-two-column">
          <section className="dashboard-panel">
            <div className="panel-heading">
              <div>
                <div className="panel-title-row">
                  <span className="panel-title-icon">▣</span>
                  <h2>My Cards</h2>
                </div>
                <p>Your saved payment cards</p>
              </div>

              <button
                type="button"
                onClick={() => setShowAddCard(!showAddCard)}
                className="soft-primary-button"
              >
                {showAddCard ? 'Close' : '+ Add Card'}
              </button>
            </div>

            {showAddCard && (
              <form onSubmit={handleAddCard} className="add-card-form">
                <div className="form-section-title"><span>＋</span> Add a new payment card</div>

                <label className="form-field">
                  <span>Card holder name</span>
                  <input
                    required
                    placeholder="Enter card holder name"
                    value={cardForm.card_holder_name}
                    onChange={(event) => setCardForm({...cardForm, card_holder_name: event.target.value})}
                  />
                </label>

                <label className="form-field">
                  <span>Card number</span>
                  <input
                    required
                    placeholder="Enter 13–19 digit card number"
                    value={cardForm.card_number}
                    onChange={(event) => setCardForm({...cardForm, card_number: event.target.value})}
                    maxLength="19"
                    inputMode="numeric"
                  />
                </label>

                <label className="form-field">
                  <span>Card type</span>
                  <select
                    value={cardForm.card_type}
                    onChange={(event) => setCardForm({...cardForm, card_type: event.target.value})}
                  >
                    <option value="VISA">Visa</option>
                    <option value="MASTERCARD">MasterCard</option>
                    <option value="RUPAY">RuPay</option>
                    <option value="AMEX">American Express</option>
                  </select>
                </label>

                <div className="form-two-columns">
                  <label className="form-field">
                    <span>Expiry month</span>
                    <input
                      required type="number" placeholder="MM" min="1" max="12"
                      value={cardForm.expiry_month}
                      onChange={(event) => setCardForm({...cardForm, expiry_month: event.target.value})}
                    />
                  </label>

                  <label className="form-field">
                    <span>Expiry year</span>
                    <input
                      required type="number" placeholder="YYYY"
                      value={cardForm.expiry_year}
                      onChange={(event) => setCardForm({...cardForm, expiry_year: event.target.value})}
                    />
                  </label>
                </div>

                {cardMessage && <div className="form-message form-message-success">{cardMessage}</div>}

                <button type="submit" disabled={cardLoading} className="full-primary-button">
                  {cardLoading ? 'Adding card...' : 'Save Card'}
                </button>
              </form>
            )}

            {cards.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">▣</div>
                <strong>No cards added yet</strong>
                <span>Add your first card to start making payments.</span>
              </div>
            ) : (
              <div className="saved-cards-list">
                {cards.map((card) => (
                  <article key={card.id} className="saved-card">
                    <div className="saved-card-glow"></div>

                    <div className="saved-card-top">
                      <div>
                        <span className="saved-card-caption">CARDPAY</span>
                        <strong>{card.card_type}</strong>
                      </div>

                      <button
                        type="button"
                        onClick={() => handleDeleteCard(card.id)}
                        className="delete-card-button"
                      >
                        Delete
                      </button>
                    </div>

                    <div className="saved-card-chip">
                      <span></span><span></span><span></span>
                    </div>

                    <div className="saved-card-number">
                      {card.masked_card_number || `**** **** **** ${card.last4}`}
                    </div>

                    <div className="saved-card-bottom">
                      <div>
                        <span>Card holder</span>
                        <strong>{card.card_holder_name}</strong>
                      </div>
                      <div>
                        <span>Valid thru</span>
                        <strong>
                          {String(card.expiry_month).padStart(2, '0')}/{card.expiry_year}
                        </strong>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>

          <section className="dashboard-panel payment-panel">
            <div className="panel-heading">
              <div>
                <div className="panel-title-row">
                  <span className="panel-title-icon payment-icon">₹</span>
                  <h2>Make Payment</h2>
                </div>
                <p>Process a secure simulated payment</p>
              </div>
              <div className="secure-pill"><span>●</span> Secure</div>
            </div>

            <div className="payment-intro">
              <div className="payment-intro-icon">✓</div>
              <div>
                <strong>Payment simulation</strong>
                <span>No real money is charged. The system simulates SUCCESS or FAILED payment results.</span>
              </div>
            </div>

            <form onSubmit={handlePayment} className="payment-form">
              <label className="form-field">
                <span>Select card</span>
                <select
                  required
                  value={paymentForm.card_id}
                  onChange={(event) => setPaymentForm({...paymentForm, card_id: event.target.value})}
                >
                  <option value="">Choose a saved card</option>
                  {cards.map((card) => (
                    <option key={card.id} value={card.id}>
                      {card.card_type} •••• {card.last4}
                    </option>
                  ))}
                </select>
              </label>

              <label className="form-field">
                <span>Amount</span>
                <div className="amount-input">
                  <span>₹</span>
                  <input
                    required type="number" min="1" step="0.01" placeholder="0.00"
                    value={paymentForm.amount}
                    onChange={(event) => setPaymentForm({...paymentForm, amount: event.target.value})}
                  />
                </div>
              </label>

              <label className="form-field">
                <span>Description</span>
                <input
                  placeholder="What is this payment for?"
                  value={paymentForm.description}
                  onChange={(event) => setPaymentForm({...paymentForm, description: event.target.value})}
                />
              </label>

              {paymentMessage && (
                <div className={`form-message ${
                  paymentMessage.includes('SUCCESS')
                    ? 'form-message-success'
                    : paymentMessage.includes('FAILED')
                      ? 'form-message-error'
                      : 'form-message-info'
                }`}>
                  {paymentMessage}
                </div>
              )}

              <button
                type="submit"
                disabled={paymentLoading || cards.length === 0}
                className="full-primary-button payment-button"
              >
                {paymentLoading ? (
                  <>
                    <span className="button-spinner"></span>
                    Processing payment...
                  </>
                ) : (
                  <>Make Payment <span>→</span></>
                )}
              </button>

              {cards.length === 0 && (
                <div className="payment-disabled-note">Add a card first to enable payments.</div>
              )}
            </form>
          </section>
        </section>

        <section className="dashboard-panel transactions-panel">
          <div className="panel-heading">
            <div>
              <div className="panel-title-row">
                <span className="panel-title-icon">↗</span>
                <h2>Recent Transactions</h2>
              </div>
              <p>Your recent payment activity</p>
            </div>

            <button type="button" onClick={loadDashboardData} className="refresh-button">
              ↻ <span>Refresh</span>
            </button>
          </div>

          {transactions.length === 0 ? (
            <div className="empty-state transaction-empty">
              <div className="empty-state-icon">↗</div>
              <strong>No transactions found</strong>
              <span>Your payment activity will appear here.</span>
            </div>
          ) : (
            <div className="transaction-table-wrap">
              <table className="transaction-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Payment ID</th>
                    <th>Card</th>
                    <th>Amount</th>
                    <th>Status</th>
                    <th>Description</th>
                    <th>Date</th>
                  </tr>
                </thead>

                <tbody>
                  {transactions.map((transaction) => (
                    <tr key={transaction.id}>
                      <td><span className="transaction-id">#{transaction.id}</span></td>
                      <td>{transaction.payment_id || '-'}</td>
                      <td>
                        <span className="transaction-card">
                          •••• {transaction.last4 || transaction.card?.last4 || ''}
                        </span>
                      </td>
                      <td>
                        <strong className="transaction-amount">
                          ₹{Number(transaction.amount || 0).toFixed(2)}
                        </strong>
                      </td>
                      <td>
                        <span className={`status-badge status-${String(transaction.status || '').toLowerCase()}`}>
                          <span></span>
                          {transaction.status}
                        </span>
                      </td>
                      <td className="transaction-description">{transaction.description || '-'}</td>
                      <td className="transaction-date">
                        {transaction.created_at ? new Date(transaction.created_at).toLocaleString() : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>

        {isAdmin && (
          <section className="admin-dashboard-section">
            <div className="admin-section-heading">
              <div>
                <div className="admin-eyebrow">ADMIN CONTROL CENTER</div>
                <h2>Admin Dashboard</h2>
                <p>Monitor users, cards, transactions, and daily payment activity.</p>
              </div>
              <div className="admin-actions">
                <button
                  type="button"
                  className="admin-refresh-button"
                  onClick={() => loadAdminData()}
                  disabled={adminLoading}
                >
                  {adminLoading ? 'Refreshing...' : '↻ Refresh Data'}
                </button>
                <button
                  type="button"
                  className="admin-export-button"
                  onClick={handleExportCsv}
                  disabled={csvLoading}
                >
                  {csvLoading ? 'Exporting...' : '↓ Export CSV'}
                </button>
              </div>
            </div>

            {adminError && <div className="admin-error-message">{adminError}</div>}

            <div className="admin-summary-grid">
              <div className="admin-summary-card admin-summary-blue">
                <span className="admin-summary-icon">♙</span>
                <span className="admin-summary-label">Total Users</span>
                <strong>{adminSummary?.overall_summary?.total_users ?? adminUsers.length}</strong>
              </div>
              <div className="admin-summary-card admin-summary-teal">
                <span className="admin-summary-icon">▣</span>
                <span className="admin-summary-label">Total Cards</span>
                <strong>{adminSummary?.overall_summary?.total_cards ?? adminCards.length}</strong>
              </div>
              <div className="admin-summary-card admin-summary-purple">
                <span className="admin-summary-icon">↗</span>
                <span className="admin-summary-label">Transactions</span>
                <strong>{adminSummary?.overall_summary?.total_transactions ?? adminTransactions.length}</strong>
              </div>
              <div className="admin-summary-card admin-summary-green">
                <span className="admin-summary-icon">✓</span>
                <span className="admin-summary-label">Successful</span>
                <strong>{adminSummary?.overall_summary?.successful_payments ?? 0}</strong>
              </div>
              <div className="admin-summary-card admin-summary-red">
                <span className="admin-summary-icon">!</span>
                <span className="admin-summary-label">Failed</span>
                <strong>{adminSummary?.overall_summary?.failed_payments ?? 0}</strong>
              </div>
              <div className="admin-summary-card admin-summary-gold">
                <span className="admin-summary-icon">₹</span>
                <span className="admin-summary-label">Payment Volume</span>
                <strong>₹{Number(adminSummary?.overall_summary?.total_payment_amount ?? 0).toFixed(2)}</strong>
              </div>
            </div>

            <div className="admin-daily-card">
              <div>
                <span className="admin-card-kicker">TODAY'S PAYMENT SUMMARY</span>
                <h3>{adminSummary?.daily_summary?.date || 'Today'}</h3>
              </div>
              <div className="admin-daily-stats">
                <div><span>Transactions</span><strong>{adminSummary?.daily_summary?.total_transactions ?? 0}</strong></div>
                <div><span>Success</span><strong>{adminSummary?.daily_summary?.successful_payments ?? 0}</strong></div>
                <div><span>Failed</span><strong>{adminSummary?.daily_summary?.failed_payments ?? 0}</strong></div>
                <div><span>Pending</span><strong>{adminSummary?.daily_summary?.pending_payments ?? 0}</strong></div>
                <div><span>Amount</span><strong>₹{Number(adminSummary?.daily_summary?.total_payment_amount ?? 0).toFixed(2)}</strong></div>
              </div>
            </div>

            <div className="admin-two-column">
              <section className="admin-table-card">
                <div className="admin-table-heading">
                  <div><h3>Users</h3><span>{adminUsers.length} registered users</span></div>
                </div>
                <div className="admin-table-wrap">
                  <table className="admin-table">
                    <thead><tr><th>User</th><th>Email</th><th>Role</th><th>Status</th></tr></thead>
                    <tbody>
                      {adminUsers.map((user) => (
                        <tr key={user.id}>
                          <td><strong>{user.username}</strong></td>
                          <td>{user.email}</td>
                          <td><span className={`admin-role ${user.is_staff ? 'admin-role-admin' : ''}`}>{user.is_staff ? 'Admin' : 'User'}</span></td>
                          <td><span className={`admin-status ${user.is_active ? 'active' : 'inactive'}`}>{user.is_active ? 'Active' : 'Inactive'}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="admin-table-card">
                <div className="admin-table-heading">
                  <div><h3>Saved Cards</h3><span>{adminCards.length} cards</span></div>
                </div>
                <div className="admin-table-wrap">
                  <table className="admin-table">
                    <thead><tr><th>Holder</th><th>Card</th><th>Type</th><th>Expiry</th></tr></thead>
                    <tbody>
                      {adminCards.map((card) => (
                        <tr key={card.id}>
                          <td><strong>{card.card_holder_name}</strong></td>
                          <td>{card.masked_card_number || `**** **** **** ${card.last4}`}</td>
                          <td>{card.card_type}</td>
                          <td>{String(card.expiry_month).padStart(2, '0')}/{card.expiry_year}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </div>

            <section className="admin-table-card admin-transactions-card">
              <div className="admin-table-heading">
                <div><h3>All Transactions</h3><span>Latest admin transaction records</span></div>
                <button type="button" onClick={handleExportCsv} className="admin-small-export" disabled={csvLoading}>
                  {csvLoading ? 'Exporting...' : 'Export CSV'}
                </button>
              </div>
              <div className="admin-table-wrap">
                <table className="admin-table admin-transactions-table">
                  <thead><tr><th>ID</th><th>Payment ID</th><th>Card</th><th>Amount</th><th>Status</th><th>Description</th><th>Date</th></tr></thead>
                  <tbody>
                    {adminTransactions.map((transaction) => (
                      <tr key={transaction.id}>
                        <td><strong>#{transaction.id}</strong></td>
                        <td>{transaction.payment_id || '-'}</td>
                        <td>•••• {transaction.card_last4 || '-'}</td>
                        <td><strong>₹{Number(transaction.amount || 0).toFixed(2)}</strong></td>
                        <td><span className={`status-badge status-${String(transaction.status || '').toLowerCase()}`}><span></span>{transaction.status}</span></td>
                        <td className="admin-description">{transaction.description || '-'}</td>
                        <td>{transaction.created_at ? new Date(transaction.created_at).toLocaleString() : '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </section>
        )}

      <footer className="dashboard-footer">
        <span>© 2026 CardPay Financial Platform</span>
        <span>•</span>
        <span>Secure Digital Payments</span>
        <span>•</span>
        <span>Protected Session</span>
      </footer>
    </div>
  )
}


export default App
