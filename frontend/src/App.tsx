import { useState, useEffect } from 'react';
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import { getDailyData, getDownloadUrl, getAnalysisData, getAdvancedAnalysis, type InvestorData, type TopStock } from './api';
import './App.css';

function App() {
  const [date, setDate] = useState<string>(new Date().toISOString().slice(0, 10).replace(/-/g, ''));
  const [activeTab, setActiveTab] = useState<string>('foreigner');
  const [data, setData] = useState<InvestorData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Download State
  const [dateRange, setDateRange] = useState<[Date | null, Date | null]>([new Date(), new Date()]);
  const [startDate, endDate] = dateRange;

  const [currentPage, setCurrentPage] = useState<'home' | 'analysis'>('home');

  /* Analysis State */
  const [analysisDays, setAnalysisDays] = useState<number>(7);
  const [analysisInvestor, setAnalysisInvestor] = useState<string>('foreigner');
  const [analysisData, setAnalysisData] = useState<InvestorData | null>(null);

  useEffect(() => {
    if (currentPage === 'home') fetchData();
    if (currentPage === 'analysis') fetchAnalysisData();
  }, [date, activeTab, currentPage, analysisDays, analysisInvestor]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getDailyData(date, activeTab);
      setData(result);
      if (result.date && result.date !== date) {
        setDate(result.date);
      }
    } catch (err) {
      console.error(err);
      setError('Data not found for this date/investor.');
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const fetchAnalysisData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch both aggregated trend and advanced analysis
      const trendResult = await getAnalysisData(analysisDays, analysisInvestor);

      // Only fetch advanced analysis if days <= 30 to avoid timeout, otherwise we warn or skip?
      // For now, let's try fetching it. ThreadPool should handle ~30 days fine.
      let advancedResult: InvestorData = { consecutive: [], new_inflow: [], buy: [], sell: [], date: '' };
      try {
        advancedResult = await getAdvancedAnalysis(analysisDays, analysisInvestor);
      } catch (e) {
        console.warn("Advanced analysis failed or timeout", e);
      }

      setAnalysisData({
        ...trendResult,
        consecutive: advancedResult.consecutive,
        new_inflow: advancedResult.new_inflow,
        start_date: advancedResult.start_date || trendResult.start_date,
        end_date: advancedResult.end_date || trendResult.end_date
      });

    } catch (err) {
      console.error(err);
      setError('Analysis data not found for this period.');
      setAnalysisData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!startDate || !endDate) return;

    // Format dates as YYYYMMDD
    const formatDate = (date: Date) => {
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      return `${year}${month}${day}`;
    };

    const start = formatDate(startDate);
    const end = formatDate(endDate);
    const url = getDownloadUrl(start, end, ['foreigner', 'individual', 'institution']);
    window.location.href = url;
  };

  const formatAmount = (amount: number) => {
    // Convert to 100 Million Won (억)
    return (amount / 100000000).toLocaleString(undefined, { maximumFractionDigits: 1 }) + ' 억';
  };

  const formatFluctuation = (rate?: number) => {
    if (rate === undefined || rate === null) return '-';
    // Korean stock market: Red is Up (Rise), Blue is Down (Fall).
    const upColor = '#ff6b6b'; // Light Red
    const downColor = '#60a5fa'; // Light Blue
    const finalColor = rate > 0 ? upColor : rate < 0 ? downColor : 'var(--text-secondary)';

    return <span style={{ color: finalColor, fontWeight: 'bold' }}>{rate > 0 ? '+' : ''}{rate}%</span>;
  };

  return (
    <div className="app-container">
      <nav className="main-nav">
        <div className="nav-logo">StockInsight</div>
        <div className="nav-links">
          <button
            className={`nav-item ${currentPage === 'home' ? 'active' : ''}`}
            onClick={() => setCurrentPage('home')}
          >
            데이터 추출
          </button>
          <button
            className={`nav-item ${currentPage === 'analysis' ? 'active' : ''}`}
            onClick={() => setCurrentPage('analysis')}
          >
            분석
          </button>
        </div>
      </nav>

      <header className="header">
        <h1>{currentPage === 'home' ? '주식 데이터 추출 사이트' : '투자자 동향 심층 분석'}</h1>
        <p className="subtitle">
          {currentPage === 'home'
            ? '외국인 / 기관 / 개인 순매수 상위 종목 분석'
            : `지난 ${analysisDays}일간 ${analysisInvestor === 'foreigner' ? '외국인' : analysisInvestor === 'individual' ? '개인' : '기관'} 투자 패턴 분석`}
        </p>
      </header>

      {currentPage === 'home' ? (
        <>
          <div className="controls">
            <label className="date-input-label">
              Target Date:
              <input
                type="date"
                value={date.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')}
                onChange={(e) => setDate(e.target.value.replace(/-/g, ''))}
                className="date-input"
              />
            </label>

            <div className="tabs">
              {['foreigner', 'individual', 'institution'].map((tab) => (
                <button
                  key={tab}
                  className={`tab-btn ${activeTab === tab ? 'active' : ''}`}
                  onClick={() => setActiveTab(tab)}
                >
                  {tab === 'foreigner' ? '외국인' : tab === 'individual' ? '개인' : '기관'}
                </button>
              ))}
            </div>
          </div>

          {loading && (
            <div className="loading-overlay">
              <div className="spinner"></div>
              <div className="loading-text">데이터를 불러오는 중입니다...</div>
            </div>
          )}
          {error && <div className="error">{error}</div>}

          {data && (
            <div className="data-grid">
              <div className="card net-buy">
                <h2>🔥 Net Buy Top 100</h2>
                <div className="table-wrapper">
                  <table>
                    <thead>
                      <tr>
                        <th>Rank</th>
                        <th>Stock</th>
                        <th>Price</th>
                        <th>Net Buy (KRW)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.buy.map((stock: TopStock) => (
                        <tr key={stock.ticker}>
                          <td className="rank">{stock.rank}</td>
                          <td className="stock-name">{stock.name}</td>
                          <td className="price">{stock.close_price?.toLocaleString()}</td>
                          <td className="amount positive">{formatAmount(stock.net_buy_amount)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="card net-sell">
                <h2>❄️ Net Sell Top 100</h2>
                <div className="table-wrapper">
                  <table>
                    <thead>
                      <tr>
                        <th>Rank</th>
                        <th>Stock</th>
                        <th>Price</th>
                        <th>Net Buy (KRW)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.sell.map((stock: TopStock) => (
                        <tr key={stock.ticker}>
                          <td className="rank">{stock.rank}</td>
                          <td className="stock-name">{stock.name}</td>
                          <td className="price">{stock.close_price?.toLocaleString()}</td>
                          <td className="amount negative">{formatAmount(stock.net_buy_amount)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          <footer className="download-section">
            <h3>Download Data (CSV)</h3>

            <div className="download-controls">
              <div className="date-picker-wrapper">
                <DatePicker
                  selectsRange={true}
                  startDate={startDate}
                  endDate={endDate}
                  onChange={(update) => {
                    setDateRange(update);
                  }}
                  className="custom-datepicker"
                  dateFormat="yyyy-MM-dd"
                  placeholderText="Select date range"
                />
              </div>
              <button onClick={handleDownload} className="download-btn">
                Download ZIP
              </button>
            </div>
          </footer>
        </>
      ) : (
        <>
          <div className="controls">
            <div className="date-input-label">
              분석 기간 (일):
              <input
                type="number"
                min="1"
                max="30"
                className="date-input"
                value={analysisDays}
                onChange={(e) => {
                  let val = parseInt(e.target.value);
                  if (isNaN(val)) val = 1;
                  if (val < 1) val = 1;
                  if (val > 30) val = 30;
                  setAnalysisDays(val);
                }}
                style={{ width: '80px', textAlign: 'right', paddingRight: '0.5rem' }}
              />
              <span style={{ marginLeft: '0.5rem', fontSize: '0.9rem', color: '#888' }}>(1~30일)</span>
            </div>

            <div className="tabs">
              {['foreigner', 'individual', 'institution'].map((tab) => (
                <button
                  key={tab}
                  className={`tab-btn ${analysisInvestor === tab ? 'active' : ''}`}
                  onClick={() => setAnalysisInvestor(tab)}
                >
                  {tab === 'foreigner' ? '외국인' : tab === 'individual' ? '개인' : '기관'}
                </button>
              ))}
            </div>
          </div>

          {loading && (
            <div className="loading-overlay">
              <div className="spinner"></div>
              <div className="loading-text">{analysisDays}일간의 데이터를 분석하고 있습니다...</div>
            </div>
          )}
          {error && <div className="error">{error}</div>}

          {analysisData && analysisData.start_date && (
            <div style={{ textAlign: 'center', marginBottom: '1rem', color: 'var(--text-secondary)', fontSize: '1.1rem' }}>
              📅 조회 기간: <span style={{ color: 'var(--text-primary)', fontWeight: 'bold' }}>{analysisData.start_date}</span> ~ <span style={{ color: 'var(--text-primary)', fontWeight: 'bold' }}>{analysisData.end_date}</span>
            </div>
          )}

          {analysisData && (
            <div className="data-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))' }}>
              {/* Card 1: Consecutive Buy */}
              <div className="card">
                <h2>🚀 {analysisDays}일 연속 순매수</h2>
                <div className="table-wrapper">
                  <table>
                    <thead>
                      <tr>
                        <th>Stock</th>
                        <th>Price</th>
                        <th>Chg%</th>
                        <th>Latest Net Buy</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analysisData.consecutive?.length === 0 ? (
                        <tr><td colSpan={4} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>조건에 맞는 종목이 없습니다.</td></tr>
                      ) : (
                        analysisData.consecutive?.map((stock: TopStock) => (
                          <tr key={stock.ticker}>
                            <td className="stock-name">{stock.name}</td>
                            <td>{stock.close_price?.toLocaleString()}</td>
                            <td>{formatFluctuation(stock.percent_change)}</td>
                            <td className="amount positive">{formatAmount(stock.net_buy_amount)}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Card 2: New Inflow */}
              <div className="card">
                <h2>✨ 최초 수급 유입 (Turnaround)</h2>
                <div className="table-wrapper">
                  <table>
                    <thead>
                      <tr>
                        <th>Stock</th>
                        <th>Price</th>
                        <th>Chg%</th>
                        <th>Latest Net Buy</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analysisData.new_inflow?.length === 0 ? (
                        <tr><td colSpan={4} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>조건에 맞는 종목이 없습니다.</td></tr>
                      ) : (
                        analysisData.new_inflow?.map((stock: TopStock) => (
                          <tr key={stock.ticker}>
                            <td className="stock-name">{stock.name}</td>
                            <td>{stock.close_price?.toLocaleString()}</td>
                            <td>{formatFluctuation(stock.percent_change)}</td>
                            <td className="amount positive">{formatAmount(stock.net_buy_amount)}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Card 3: Total Net Buy (Legacy) */}
              <div className="card">
                <h2>💰 기간 누적 순매수 Top</h2>
                <div className="table-wrapper">
                  <table>
                    <thead>
                      <tr>
                        <th>Rank</th>
                        <th>Stock</th>
                        <th>Price</th>
                        <th>Chg%</th>
                        <th>Total Net Buy</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analysisData.buy.slice(0, 50).map((stock: TopStock) => (
                        <tr key={stock.ticker}>
                          <td className="rank">{stock.rank}</td>
                          <td className="stock-name">{stock.name}</td>
                          <td>{stock.close_price?.toLocaleString()}</td>
                          <td>{formatFluctuation(stock.percent_change)}</td>
                          <td className="amount positive">{formatAmount(stock.net_buy_amount)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default App;
