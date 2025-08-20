import React, { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { supabase } from '@supabase/supabase-js';

// The base URL for your Flask backend.
const API_BASE_URL = 'http://127.0.0.1:5000';

const App = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [dashboardData, setDashboardData] = useState(null);
  const [error, setError] = useState(null);
  const [view, setView] = useState('login');

  // Handle the login form submission.
  const handleLogin = async (e) => {
    e.preventDefault();
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        // Login successful. Now fetch the dashboard data using the new credentials.
        await fetchDashboardData(data);
        setView('dashboard');
      } else {
        setError(data.error || 'Login failed. Please check your credentials.');
      }
    } catch (e) {
      console.error('Login fetch error:', e);
      setError('Failed to connect to the backend server.');
    }
  };

  // Fetch dashboard data from the Flask backend.
  const fetchDashboardData = async (authData) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/dashboard_data`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          company_id: authData.company_id,
          supabase_url: authData.supabase_url,
          supabase_anon_key: authData.supabase_anon_key,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      if (data.success) {
        setDashboardData(data);
      } else {
        setError(data.error);
      }
    } catch (e) {
      console.error('Dashboard data fetch error:', e);
      setError('Failed to fetch dashboard data. Make sure the Flask server is running.');
    }
  };

  // Handle logout
  const handleLogout = () => {
    setDashboardData(null);
    setEmail('');
    setPassword('');
    setView('login');
  };

  return (
    <div className="font-sans antialiased text-gray-900 dark:text-gray-100 bg-gray-100 dark:bg-gray-900 min-h-screen p-8">
      {view === 'login' && (
        <div className="flex flex-col items-center justify-center min-h-screen">
          <h1 className="text-4xl font-bold mb-4 text-center">Zappy Bots Dashboard</h1>
          <p className="text-lg mb-8 text-center">Please log in to view your statistics.</p>
          <div className="bg-white dark:bg-gray-800 p-8 rounded-lg shadow-xl w-full max-w-sm">
            <h2 className="text-2xl font-semibold mb-6 text-center">Login</h2>
            <form onSubmit={handleLogin} className="flex flex-col space-y-4">
              <input
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
              <button
                type="submit"
                className="w-full bg-blue-600 text-white font-semibold py-3 px-6 rounded-lg hover:bg-blue-700 transition-colors duration-200"
              >
                Log In
              </button>
            </form>
            {error && <p className="text-red-500 mt-4 text-center">{error}</p>}
          </div>
        </div>
      )}
      {view === 'dashboard' && dashboardData && (
        <div className="max-w-7xl mx-auto">
          <header className="flex justify-between items-center mb-10">
            <h1 className="text-4xl font-extrabold text-blue-600 dark:text-blue-400">Dashboard</h1>
            <button
              onClick={handleLogout}
              className="px-6 py-2 bg-red-600 text-white rounded-full hover:bg-red-700 transition-colors duration-200 shadow-lg"
            >
              Log Out
            </button>
          </header>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
            <StatCard title="Total Messages" value={dashboardData.stats.total_messages || 0} />
            <StatCard title="Total Conversions" value={dashboardData.stats.total_conversions || 0} />
            <StatCard title="Total Recipients" value={dashboardData.stats.total_recipients || 0} />
            <StatCard title="Avg. Response Time (ms)" value={dashboardData.stats.avg_response_time_ms || 0} />
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Total Messages Trend</h2>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={dashboardData.chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="date" stroke="#6b7280" />
                <YAxis stroke="#6b7280" />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="total_messages" stroke="#2563eb" activeDot={{ r: 8 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
      {view === 'dashboard' && !dashboardData && !error && (
        <div className="flex items-center justify-center min-h-screen">
          <p className="text-xl text-gray-700 dark:text-gray-300">Loading dashboard data...</p>
        </div>
      )}
    </div>
  );
};

// A reusable component for displaying a single statistic card.
const StatCard = ({ title, value }) => (
  <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
    <h3 className="text-lg font-medium text-gray-500 dark:text-gray-400 mb-2">{title}</h3>
    <p className="text-3xl font-bold text-blue-600 dark:text-blue-400">{value}</p>
  </div>
);

export default App;
