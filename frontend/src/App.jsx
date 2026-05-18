import { useState, useEffect } from 'react';

function App() {
  const [activeTab, setActiveTab] = useState('new'); // new, active, past
  
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-8 font-sans">
      <div className="max-w-5xl mx-auto">
        <header className="mb-8 border-b border-slate-700 pb-4">
          <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-sky-400 to-indigo-400">
            Crystal Market Operations
          </h1>
          <p className="text-slate-400 mt-2">Supplier outreach and automated negotiations</p>
        </header>

        <nav className="flex space-x-4 mb-8">
          <button 
            onClick={() => setActiveTab('new')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${activeTab === 'new' ? 'bg-sky-500 text-white' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'}`}>
            New Campaign
          </button>
          <button 
            onClick={() => setActiveTab('active')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${activeTab === 'active' ? 'bg-sky-500 text-white' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'}`}>
            Active Job Insights
          </button>
          <button 
            onClick={() => setActiveTab('past')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${activeTab === 'past' ? 'bg-sky-500 text-white' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'}`}>
            Past Jobs Archive
          </button>
        </nav>

        <main className="bg-slate-800/50 rounded-2xl p-6 border border-slate-700/50 shadow-xl backdrop-blur-sm">
          {activeTab === 'new' && <NewCampaign />}
          {activeTab === 'active' && <ActiveJob />}
          {activeTab === 'past' && <PastJobs />}
        </main>
      </div>
    </div>
  );
}

function NewCampaign() {
  const [suppliers, setSuppliers] = useState([]);
  const [selectedEmails, setSelectedEmails] = useState(new Set());
  const [query, setQuery] = useState('');
  
  useEffect(() => {
    fetch('http://localhost:8000/api/suppliers')
      .then(res => res.json())
      .then(data => setSuppliers(data))
      .catch(err => console.error(err));
  }, []);

  const toggleSupplier = (email) => {
    const newSelected = new Set(selectedEmails);
    if (newSelected.has(email)) newSelected.delete(email);
    else newSelected.add(email);
    setSelectedEmails(newSelected);
  };

  const startJob = async () => {
    if (selectedEmails.size === 0 || !query) return alert('Select suppliers and enter a query');
    try {
      const res = await fetch('http://localhost:8000/api/jobs/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chemical_query: query,
          supplier_emails: Array.from(selectedEmails)
        })
      });
      const data = await res.json();
      alert(`Job Started! ID: ${data.job_id}`);
    } catch (e) {
      console.error(e);
      alert('Failed to start job');
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-sky-400">Configure New Outreach</h2>
      
      <div>
        <label className="block text-sm font-medium text-slate-400 mb-2">Chemicals Query</label>
        <textarea 
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. 20,000 MT Methanol CFR Singapore..."
          className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-slate-200 focus:ring-2 focus:ring-sky-500 focus:outline-none"
          rows={3}
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-400 mb-2">Select Target Suppliers</label>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-60 overflow-y-auto pr-2">
          {suppliers.map((sup, idx) => (
            <div 
              key={idx} 
              onClick={() => toggleSupplier(sup.email_id)}
              className={`flex items-center p-3 rounded-lg border cursor-pointer transition-colors ${selectedEmails.has(sup.email_id) ? 'bg-sky-900/30 border-sky-500' : 'bg-slate-900 border-slate-700 hover:border-slate-500'}`}
            >
              <input 
                type="checkbox" 
                checked={selectedEmails.has(sup.email_id)} 
                readOnly
                className="w-5 h-5 rounded border-slate-600 text-sky-500 bg-slate-800 focus:ring-sky-500 focus:ring-offset-slate-900 mr-3"
              />
              <div>
                <p className="font-medium text-slate-200">{sup.company_name}</p>
                <p className="text-xs text-slate-500">{sup.email_id}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <button 
        onClick={startJob}
        className="w-full py-3 px-4 bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-500 hover:to-indigo-500 text-white font-bold rounded-lg shadow-lg transition-transform active:scale-[0.98]">
        Launch Campaign
      </button>
    </div>
  );
}

function ActiveJob() {
  const [insights, setInsights] = useState([]);
  
  const refreshInsights = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/jobs/1/insights/refresh', { method: 'POST' });
      const data = await res.json();
      alert(data.message);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold text-sky-400">Live Insights Dashboard</h2>
        <button onClick={refreshInsights} className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm font-medium transition-colors">
          Refresh Data
        </button>
      </div>
      
      {insights.length === 0 ? (
        <div className="text-center py-12 bg-slate-900/50 rounded-lg border border-slate-800 border-dashed">
          <p className="text-slate-500">No insights extracted yet. Click refresh to poll inbox.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          {/* Table goes here */}
        </div>
      )}
    </div>
  );
}

function PastJobs() {
  return (
    <div>
      <h2 className="text-xl font-semibold text-sky-400 mb-4">Historical Archives (GCS)</h2>
      <p className="text-slate-500">Historical jobs will be loaded here from your GCS bucket.</p>
    </div>
  );
}

export default App;
