import { useState, useEffect } from 'react';
import { 
  Activity, Send, Archive, RefreshCw, CheckCircle2, 
  AlertCircle, Clock, Users, DollarSign, Award, 
  FileText, ChevronRight, Search, PlusCircle, Check,
  Sparkles, Mail, Database, Ban, Inbox, ArrowRight, Eye, X
} from 'lucide-react';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

const apiUrl = (path) => `${API_BASE_URL}${path}`;

function App() {
  const [jobs, setJobs] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [loadingSuppliers, setLoadingSuppliers] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [selectedJobDetail, setSelectedJobDetail] = useState(null);
  const [toast, setToast] = useState(null);
  const [showEmailModal, setShowEmailModal] = useState(false);
  const [selectedEmail, setSelectedEmail] = useState(null);
  
  // States for Launchpad (Column 1)
  const [query, setQuery] = useState('');
  const [selectedSuppliers, setSelectedSuppliers] = useState(new Set());
  const [launching, setLaunching] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [userEmail, setUserEmail] = useState(() => 
    localStorage.getItem('userEmail') || 'amit.gupta@coralbayadvisory.com'
  );

  const PRESETS = [
    "20,000 MT Methanol CFR Singapore - delivery late June 2026",
    "15,000 MT Acetic Acid CIF Mumbai India - urgent mid-July arrival",
    "40,000 MT Urea FOB Qafco Qatar - August loading schedule"
  ];

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const fetchJobs = async (selectNewest = false) => {
    setLoadingJobs(true);
    try {
      const res = await fetch(apiUrl('/api/jobs'));
      const data = await res.json();
      setJobs(data);
      if (data.length > 0) {
        if (selectNewest || !selectedJobId) {
          setSelectedJobId(data[0].id);
        }
      }
    } catch (e) {
      console.error(e);
      showToast('Failed to load campaigns', 'error');
    } finally {
      setLoadingJobs(false);
    }
  };

  const fetchSuppliers = async () => {
    setLoadingSuppliers(true);
    try {
      const res = await fetch(apiUrl('/api/suppliers'));
      const data = await res.json();
      setSuppliers(data);
    } catch (e) {
      console.error(e);
      showToast('Failed to load suppliers list', 'error');
    } finally {
      setLoadingSuppliers(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    fetchSuppliers();
  }, []);

  // Fetch detailed job info when selectedJobId changes
  useEffect(() => {
    if (selectedJobId) {
      const fetchJobDetail = async () => {
        try {
          const res = await fetch(apiUrl(`/api/jobs/${selectedJobId}`));
          if (res.ok) {
            const data = await res.json();
            setSelectedJobDetail(data);
          }
        } catch (e) {
          console.error('Failed to fetch job details:', e);
        }
      };
      fetchJobDetail();
    }
  }, [selectedJobId]);

  // Compute stats
  const activeCampaignsCount = jobs.filter(j => j.status === 'active').length;
  
  // Count replied supplier states
  let totalReplied = 0;
  let totalSuppliersContacted = 0;
  jobs.forEach(j => {
    totalSuppliersContacted += j.suppliers?.length || 0;
    j.suppliers?.forEach(s => {
      if (s.replied) totalReplied++;
    });
  });

  // Calculate average price
  let prices = [];
  jobs.forEach(j => {
    j.insights?.forEach(ins => {
      if (ins.price) {
        const val = parseFloat(ins.price.replace(/[^0-9.]/g, ''));
        if (!isNaN(val)) prices.push(val);
      }
    });
  });
  const avgPrice = prices.length > 0 
    ? `$${(prices.reduce((a, b) => a + b, 0) / prices.length).toFixed(1)} / MT` 
    : 'N/A';

  const selectedJob = selectedJobDetail?.job || jobs.find(j => j.id === selectedJobId);

  // Actions
  const handleToggleSupplier = (email) => {
    const next = new Set(selectedSuppliers);
    if (next.has(email)) next.delete(email);
    else next.add(email);
    setSelectedSuppliers(next);
  };

  const handleSelectAllSuppliers = () => {
    if (selectedSuppliers.size === suppliers.length) {
      setSelectedSuppliers(new Set());
    } else {
      setSelectedSuppliers(new Set(suppliers.map(s => s.email_id)));
    }
  };

  const handleLaunchCampaign = async () => {
    if (!query.trim()) return showToast('Please enter a chemical procurement query', 'error');
    if (selectedSuppliers.size === 0) return showToast('Please select at least one supplier', 'error');
    if (!userEmail.trim()) return showToast('Please enter your email address', 'error');

    setLaunching(true);
    try {
      const res = await fetch(apiUrl('/api/jobs/start'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chemical_query: query,
          supplier_emails: Array.from(selectedSuppliers),
          user_email: userEmail
        })
      });
      const data = await res.json();
      // Save user email to localStorage
      localStorage.setItem('userEmail', userEmail);
      showToast(`Outreach Campaign #${data.job_id} launched successfully!`);
      setQuery('');
      setSelectedSuppliers(new Set());
      await fetchJobs(true); // Select the newest launched job
    } catch (e) {
      console.error(e);
      showToast('Failed to start campaign', 'error');
    } finally {
      setLaunching(false);
    }
  };

  const handleScanInbox = async () => {
    if (!selectedJob) return;
    setRefreshing(true);
    try {
      const res = await fetch(apiUrl(`/api/jobs/${selectedJob.id}/insights/refresh`), { method: 'POST' });
      const data = await res.json();
      showToast(data.message);
      await fetchJobs();
    } catch (e) {
      console.error(e);
      showToast('Failed to scan inbox', 'error');
    } finally {
      setRefreshing(false);
    }
  };

  const handleCloseCampaign = async () => {
    if (!selectedJob) return;
    if (!window.confirm("Archive this campaign final insights to GCS?")) return;
    
    try {
      const res = await fetch(apiUrl(`/api/jobs/${selectedJob.id}/close`), { method: 'POST' });
      const data = await res.json();
      showToast(data.message);
      await fetchJobs();
    } catch (e) {
      console.error(e);
      showToast('Failed to archive campaign', 'error');
    }
  };

  const filteredSuppliers = suppliers.filter(s => 
    s.company_name?.toLowerCase().includes(searchQuery.toLowerCase()) || 
    s.email_id?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.domain?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="h-screen w-screen flex flex-col justify-between bg-slate-50 select-none overflow-hidden relative text-slate-800">
      
      {/* Toast Alert */}
      {toast && (
        <div className="fixed top-4 right-4 z-50 animate-fade-in flex items-center gap-3 px-4 py-3 rounded-xl border bg-white shadow-xl border-slate-200">
          {toast.type === 'success' ? (
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
          ) : (
            <span className="w-2 h-2 rounded-full bg-rose-500"></span>
          )}
          <span className="text-xs font-semibold text-slate-700">{toast.message}</span>
        </div>
      )}

      {/* Modern Compact Header */}
      <header className="h-[60px] bg-white border-b border-slate-200/80 px-6 flex justify-between items-center shrink-0 shadow-sm z-20">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 bg-purple-100 rounded-lg flex items-center justify-center border border-purple-250">
            <Sparkles className="w-4 h-4 text-purple-600" />
          </div>
          <div>
            <h1 className="text-base font-extrabold text-slate-900 tracking-tight leading-tight">Crystal Ops Console</h1>
            <p className="text-[10px] text-slate-500 font-medium">Automated B2B Supplier Outreach & AI Negotiation Analytics</p>
          </div>
        </div>

        {/* Global Stats bar embedded in header */}
        <div className="hidden md:flex items-center gap-6 text-xs border-l border-slate-200 pl-6 h-8">
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Live Scans:</span>
            <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-cyan-50 border border-cyan-200/80 text-cyan-700 font-bold text-[10px]">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-500 pulse-scanner"></span>
              POLLING
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Active Campaigns:</span>
            <span className="px-2 py-0.5 rounded-full bg-purple-50 border border-purple-200 text-purple-700 font-bold text-[10px]">
              {activeCampaignsCount} Active
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Average Index:</span>
            <span className="px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 font-bold text-[10px]">
              {avgPrice}
            </span>
          </div>

          <button 
            onClick={() => { fetchJobs(); fetchSuppliers(); showToast('Console dashboard synced'); }} 
            className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-500 shrink-0 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingJobs ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </header>

      {/* Main 3-Column Side-by-Side Panel System (Fits entirely on 1 screen) */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-5 p-5 min-h-0 h-[calc(100vh-100px)] overflow-hidden bg-slate-50/50">
        
        {/* ==========================================
            COLUMN 1: CAMPAIGN LAUNCHER & SUPPLIERS
            ========================================== */}
        <section className="flex flex-col h-full bg-white rounded-2xl border border-slate-200/80 p-4 shadow-sm min-h-0 overflow-hidden">
          {/* Header */}
          <div className="shrink-0 mb-3 border-b border-slate-100 pb-2">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-purple-500"></span>
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">1. Outreach Configurator</h2>
            </div>
            <p className="text-[10px] text-slate-500 mt-0.5">Specify your chemical quote criteria and target suppliers.</p>
          </div>

          <div className="flex-1 flex flex-col justify-between min-h-0 space-y-4">
            
            {/* User Email */}
            <div className="shrink-0 space-y-2">
              <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest">Your Email (for notifications)</span>
              <input 
                type="email"
                value={userEmail}
                onChange={(e) => setUserEmail(e.target.value)}
                placeholder="your.email@company.com"
                className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs text-slate-800 focus:outline-none focus:ring-1 focus:ring-purple-400 glow-pastel-indigo placeholder:text-slate-400"
              />
            </div>
            
            {/* Input Specs */}
            <div className="shrink-0 space-y-2">
              <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest">Chemical Spec Inquiry</span>
              <textarea 
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Describe chemical requirements (e.g. 20,000 MT Methanol CFR Singapore, delivery late June 2026)..."
                className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs text-slate-800 focus:outline-none focus:ring-1 focus:ring-purple-400 glow-pastel-indigo placeholder:text-slate-400"
                rows={3}
              />
              {/* Presets */}
              <div className="flex gap-1.5 flex-wrap">
                {PRESETS.map((preset, idx) => (
                  <button
                    key={idx}
                    onClick={() => setQuery(preset)}
                    className="px-2 py-1 text-[9px] font-medium text-purple-700 bg-purple-50 hover:bg-purple-100 border border-purple-200/80 rounded-md transition-colors truncate max-w-full text-left"
                  >
                    Preset {idx + 1}
                  </button>
                ))}
              </div>
            </div>

            {/* Target Suppliers Directory */}
            <div className="flex-1 flex flex-col min-h-0 space-y-2">
              <div className="flex justify-between items-center shrink-0">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Select Target Suppliers ({selectedSuppliers.size})</span>
                <button 
                  onClick={handleSelectAllSuppliers} 
                  className="text-[9px] font-bold text-purple-600 hover:text-purple-800 hover:underline"
                >
                  {selectedSuppliers.size === suppliers.length ? 'Deselect All' : 'Select All'}
                </button>
              </div>

              {/* Search Bar */}
              <div className="relative shrink-0">
                <Search className="w-3 h-3 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                <input 
                  type="text"
                  placeholder="Filter by company, email, location..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="bg-slate-50 border border-slate-200 rounded-lg pl-8 pr-2 py-1 text-[10px] text-slate-700 focus:outline-none focus:ring-1 focus:ring-purple-400 w-full"
                />
              </div>

              {/* Internally Scrollable Supplier list */}
              <div className="flex-1 overflow-y-auto border border-slate-100 rounded-xl p-1.5 space-y-1.5 bg-slate-50/50">
                {loadingSuppliers ? (
                  <div className="text-center py-8 text-[11px] text-slate-400">Loading Directory...</div>
                ) : filteredSuppliers.map((sup, idx) => {
                  const isSelected = selectedSuppliers.has(sup.email_id);
                  return (
                    <div 
                      key={idx}
                      onClick={() => handleToggleSupplier(sup.email_id)}
                      className={`p-2.5 rounded-lg border cursor-pointer flex items-center gap-2.5 transition-all duration-200 ${isSelected ? 'bg-purple-50/80 border-purple-300' : 'bg-white border-slate-100/80 hover:border-slate-250'}`}
                    >
                      <div className="shrink-0">
                        <div className={`w-3.5 h-3.5 rounded border flex items-center justify-center transition-all ${isSelected ? 'bg-purple-500 border-purple-400' : 'border-slate-300 bg-white'}`}>
                          {isSelected && <Check className="w-2.5 h-2.5 text-white stroke-[3px]" />}
                        </div>
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex justify-between items-center gap-1.5">
                          <span className="font-bold text-[10px] text-slate-800 truncate">{sup.company_name}</span>
                          <span className="text-[8px] bg-slate-200 px-1 py-0.2 rounded text-slate-500 uppercase">{sup.domain.split('.')[0]}</span>
                        </div>
                        <p className="text-[9px] text-slate-450 truncate">{sup.email_id} • {sup.domain}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Launch Button */}
            <button 
              onClick={handleLaunchCampaign}
              disabled={launching}
              className="shrink-0 w-full py-2.5 bg-purple-600 hover:bg-purple-750 text-white rounded-xl font-bold text-xs shadow-md shadow-purple-600/10 cursor-pointer flex items-center justify-center gap-2 active:scale-[0.98] transition-transform disabled:opacity-50"
            >
              {launching ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  Generating Invites...
                </>
              ) : (
                <>
                  <Send className="w-3.5 h-3.5" />
                  Launch Outreach Campaign
                </>
              )}
            </button>
          </div>
        </section>

        {/* ==========================================
            COLUMN 2: CAMPAIGN MONITOR & TIMELINES
            ========================================== */}
        <section className="flex flex-col h-full bg-white rounded-2xl border border-slate-200/80 p-4 shadow-sm min-h-0 overflow-hidden">
          {/* Header */}
          <div className="shrink-0 mb-3 border-b border-slate-100 pb-2 flex justify-between items-start">
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-cyan-500"></span>
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">2. Campaign Monitor & Status</h2>
              </div>
              <p className="text-[10px] text-slate-500 mt-0.5">Select a campaign to view status updates and manage outreach.</p>
            </div>
            {selectedJob && (
              <button
                onClick={fetchJobs}
                disabled={loadingJobs}
                className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-500 hover:text-slate-700 transition-colors disabled:opacity-50 shrink-0"
                title="Refresh campaign data"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loadingJobs ? 'animate-spin' : ''}`} />
              </button>
            )}
          </div>

          <div className="flex-1 flex flex-col justify-between min-h-0 space-y-4">
            
            {/* Job Status Report Card */}
            {selectedJob ? (
              <div className="shrink-0 bg-gradient-to-br from-cyan-50/60 to-blue-50/40 border border-cyan-100 p-3 rounded-xl space-y-2.5">
                <div className="grid grid-cols-2 gap-2.5">
                  {/* Campaign Duration */}
                  <div className="flex items-center gap-2">
                    <Clock className="w-3.5 h-3.5 text-cyan-600 shrink-0" />
                    <div className="min-w-0">
                      <span className="block text-[8px] font-bold text-slate-400 uppercase">Duration</span>
                      <span className="block text-[10px] font-bold text-slate-700">{
                        (() => {
                          const created = new Date(selectedJobDetail?.job?.created_at);
                          const now = new Date();
                          const hours = Math.floor((now - created) / (1000 * 60 * 60));
                          const mins = Math.floor(((now - created) % (1000 * 60 * 60)) / (1000 * 60));
                          return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
                        })()
                      }</span>
                    </div>
                  </div>

                  {/* Response Rate */}
                  <div className="flex items-center gap-2">
                    <Users className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                    <div className="min-w-0">
                      <span className="block text-[8px] font-bold text-slate-400 uppercase">Responses</span>
                      <span className="block text-[10px] font-bold text-slate-700">{
                        selectedJobDetail?.suppliers?.filter(s => s.replied).length || 0
                      } / {selectedJobDetail?.suppliers?.length || 0}</span>
                    </div>
                  </div>

                  {/* Insights Count */}
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-3.5 h-3.5 text-purple-600 shrink-0" />
                    <div className="min-w-0">
                      <span className="block text-[8px] font-bold text-slate-400 uppercase">Insights</span>
                      <span className="block text-[10px] font-bold text-slate-700">{selectedJobDetail?.insights?.length || 0} Extracted</span>
                    </div>
                  </div>

                  {/* Status Badge */}
                  <div className="flex items-center gap-2">
                    {selectedJobDetail?.job?.status === 'active' ? (
                      <>
                        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shrink-0"></div>
                        <span className="text-[10px] font-bold text-emerald-700">ACTIVE</span>
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                        <span className="text-[10px] font-bold text-slate-500">CLOSED</span>
                      </>
                    )}
                  </div>
                </div>

                {/* Timestamps */}
                <div className="pt-2 border-t border-cyan-100 space-y-1.5 text-[8px]">
                  <div className="flex justify-between">
                    <span className="text-slate-500 font-semibold">Created:</span>
                    <span className="text-slate-700 font-bold">{new Date(selectedJobDetail?.job?.created_at).toLocaleString()}</span>
                  </div>
                  {selectedJobDetail?.job?.closed_at && (
                    <div className="flex justify-between">
                      <span className="text-slate-500 font-semibold">Closed:</span>
                      <span className="text-slate-700 font-bold">{new Date(selectedJobDetail?.job?.closed_at).toLocaleString()}</span>
                    </div>
                  )}
                </div>
              </div>
            ) : null}

            {/* Scrollable list of campaigns in registry */}
            <div className="shrink-0 space-y-2">
              <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest">Active & Archived Registry</span>
              <div className="max-h-[160px] overflow-y-auto border border-slate-100 rounded-xl p-1.5 space-y-1 bg-slate-50/50">
                {jobs.map((job) => {
                  const isActive = job.status === 'active';
                  const isSelected = selectedJobId === job.id;
                  return (
                    <div
                      key={job.id}
                      onClick={() => setSelectedJobId(job.id)}
                      className={`p-2 rounded-lg border cursor-pointer text-left transition-all duration-200 flex justify-between items-center ${isSelected ? 'bg-cyan-50/80 border-cyan-300' : 'bg-white border-slate-100/60 hover:border-slate-250'}`}
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5">
                          <span className="font-extrabold text-[10px] text-slate-900">Campaign #{job.id}</span>
                          <span className={`text-[8px] font-extrabold px-1.5 py-0.2 rounded border ${isActive ? 'bg-cyan-50 text-cyan-700 border-cyan-200' : 'bg-slate-100 text-slate-500 border-slate-200'}`}>
                            {isActive ? 'ACTIVE' : 'ARCHIVED'}
                          </span>
                        </div>
                        <p className="text-[9px] text-slate-500 truncate mt-0.5">{job.chemical_query}</p>
                      </div>
                      <ChevronRight className="w-3.5 h-3.5 text-slate-400 shrink-0 ml-2" />
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Timelines and Targets for selected Job */}
            {selectedJob ? (
              <div className="flex-1 flex flex-col min-h-0 space-y-4 justify-between">
                
                {/* Horizontal Timeline Pipeline */}
                <div className="shrink-0 bg-slate-50/60 border border-slate-100 p-3 rounded-xl space-y-2">
                  <span className="block text-[9px] font-bold text-slate-400 uppercase tracking-widest">Outreach Phase</span>
                  <div className="grid grid-cols-4 gap-1 relative">
                    
                    {/* Background Progress bar */}
                    <div className="absolute top-[8px] left-[12.5%] right-[12.5%] h-[1.5px] bg-slate-200 z-0">
                      <div 
                        className="h-full bg-gradient-to-r from-cyan-400 to-purple-400 transition-all duration-300"
                        style={{ 
                        width: selectedJobDetail?.job?.status === 'closed' ? '100%' : selectedJobDetail?.job?.reminders_sent ? '66%' : '33%' 
                        }}
                      />
                    </div>

                    <div className="z-10 text-center space-y-0.5">
                      <div className={`w-4 h-4 rounded-full flex items-center justify-center mx-auto text-[8px] font-bold ${selectedJobDetail?.job?.status ? 'bg-cyan-500 border border-cyan-400 text-white' : 'bg-slate-100 text-slate-450 border border-slate-200'}`}>1</div>
                      <span className="block text-[8px] font-bold text-slate-600 leading-none">Sent</span>
                    </div>

                    <div className="z-10 text-center space-y-0.5">
                      <div className={`w-4 h-4 rounded-full flex items-center justify-center mx-auto text-[8px] font-bold ${selectedJobDetail?.job?.status === 'active' && !selectedJobDetail?.job?.reminders_sent ? 'bg-cyan-500 border border-cyan-400 text-white animate-pulse' : selectedJobDetail?.job?.reminders_sent || selectedJobDetail?.job?.status === 'closed' ? 'bg-cyan-500 border border-cyan-400 text-white' : 'bg-slate-100 text-slate-450 border border-slate-200'}`}>2</div>
                      <span className="block text-[8px] font-bold text-slate-600 leading-none">Polling</span>
                    </div>

                    <div className="z-10 text-center space-y-0.5">
                      <div className={`w-4 h-4 rounded-full flex items-center justify-center mx-auto text-[8px] font-bold ${selectedJobDetail?.job?.reminders_sent && selectedJobDetail?.job?.status === 'active' ? 'bg-cyan-500 border border-cyan-400 text-white animate-pulse' : selectedJobDetail?.job?.status === 'closed' ? 'bg-cyan-500 border border-cyan-400 text-white' : 'bg-slate-100 text-slate-450 border border-slate-200'}`}>3</div>
                      <span className="block text-[8px] font-bold text-slate-600 leading-none">Reminder</span>
                    </div>

                    <div className="z-10 text-center space-y-0.5">
                      <div className={`w-4 h-4 rounded-full flex items-center justify-center mx-auto text-[8px] font-bold ${selectedJobDetail?.job?.status === 'closed' ? 'bg-purple-600 border border-purple-400 text-white' : 'bg-slate-100 text-slate-450 border border-slate-200'}`}>4</div>
                      <span className="block text-[8px] font-bold text-slate-600 leading-none">Archived</span>
                    </div>
                  </div>
                </div>

                {/* Target checklist list */}
                <div className="flex-1 flex flex-col min-h-0 space-y-2">
                  <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest">Supplier Response Status</span>
                  
                  <div className="flex-1 overflow-y-auto border border-slate-100 rounded-xl p-2 space-y-1.5 bg-slate-50/50">
                    {selectedJob.suppliers?.map((sup, idx) => (
                      <div 
                        key={idx}
                        className={`p-2 rounded-lg border bg-white border-slate-100 flex justify-between items-center text-xs font-semibold`}
                      >
                        <div className="min-w-0 flex-1">
                          <span className="font-bold text-[10px] text-slate-800 block truncate">{sup.company_name || sup.email_id.split('@')[0]}</span>
                          <span className="text-[8px] text-slate-500 font-medium block truncate mt-0.5">{sup.email_id}</span>
                        </div>

                        {sup.replied ? (
                          <span className="px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 font-bold text-[9px] shrink-0 ml-2">
                            Replied
                          </span>
                        ) : selectedJob.reminders_sent ? (
                          <span className="px-2 py-0.5 rounded-full bg-rose-50 border border-rose-200 text-rose-700 font-bold text-[9px] shrink-0 ml-2 animate-pulse">
                            Reminder Sent
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded-full bg-amber-50 border border-amber-200 text-amber-700 font-bold text-[9px] shrink-0 ml-2 flex items-center gap-1">
                            <Clock className="w-2.5 h-2.5 animate-spin" style={{ animationDuration: '4s' }} />
                            Awaiting
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-6 border border-dashed border-slate-200 rounded-xl bg-slate-50/20">
                <Inbox className="w-8 h-8 text-slate-350 mb-2" />
                <p className="text-xs font-bold text-slate-400">No Campaign Selected</p>
                <p className="text-[10px] text-slate-500 mt-0.5">Please launch or select a campaign to monitor its pipeline status.</p>
              </div>
            )}
          </div>
        </section>

        {/* ==========================================
            COLUMN 3: AI-EXTRACTED BIDS & ACTIONS
            ========================================== */}
        <section className="flex flex-col h-full bg-white rounded-2xl border border-slate-200/80 p-4 shadow-sm min-h-0 overflow-hidden">
          {/* Header */}
          <div className="shrink-0 mb-3 border-b border-slate-100 pb-2 flex justify-between items-start">
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">3. Extracted Bids & Offers</h2>
              </div>
              <p className="text-[10px] text-slate-500 mt-0.5">AI-extracted terms and pricing from supplier replies.</p>
            </div>
            {selectedJob && (
              <button
                onClick={handleScanInbox}
                disabled={refreshing}
                className="p-1.5 rounded-lg border border-cyan-200 bg-cyan-50 hover:bg-cyan-100 text-cyan-600 transition-colors disabled:opacity-50 shrink-0"
                title="Refresh insights from inbox"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
              </button>
            )}
          </div>

          <div className="flex-1 flex flex-col justify-between min-h-0 space-y-4">
            
            {/* Main Extracted Offers Table Container */}
            <div className="flex-1 flex flex-col min-h-0 space-y-2">
              <div className="flex justify-between items-center shrink-0">
                <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                  Bid Details {selectedJobDetail?.insights?.length > 0 && `(${selectedJobDetail?.insights?.length})`}
                </span>
                {selectedJob?.insights?.length > 0 && (
                  <span className="text-[9px] font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                    Updated: {new Date().toLocaleTimeString()}
                  </span>
                )}
              </div>
              
              <div className="flex-1 overflow-hidden border border-slate-100 rounded-xl bg-slate-50/20 flex flex-col">
                {selectedJobDetail && selectedJobDetail.insights?.length > 0 ? (
                  <div className="flex-1 overflow-y-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="border-b border-slate-150 text-[8px] font-bold text-slate-400 uppercase bg-slate-50 shrink-0 sticky top-0">
                          <th className="p-2.5 text-left">Supplier</th>
                          <th className="p-2.5 text-left">Contact</th>
                          <th className="p-2.5 text-left">Product</th>
                          <th className="p-2.5 text-right">Price Offer</th>
                          <th className="p-2.5 text-left">Qty</th>
                          <th className="p-2.5 text-left">Delivery</th>
                          <th className="p-2.5 text-center w-10">Email</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 text-[9px]">
                        {selectedJobDetail?.insights?.map((ins, idx) => (
                          <tr key={idx} className="hover:bg-emerald-50/40 transition-colors bg-white font-medium text-slate-700">
                            <td className="p-2.5">
                              <span className="font-bold text-slate-900 block truncate">{ins.supplier}</span>
                            </td>
                            <td className="p-2.5">
                              <span className="text-[8px] font-semibold text-slate-600 block truncate">{ins.contact_person || 'N/A'}</span>
                            </td>
                            <td className="p-2.5">
                              <span className="block truncate text-slate-700">{ins.product}</span>
                              <span className="text-[8px] text-slate-500 block truncate">{ins.quantity}</span>
                            </td>
                            <td className="p-2.5 text-right">
                              <span className="px-2 py-0.5 rounded-md bg-emerald-50 border border-emerald-250 text-emerald-700 font-extrabold text-[8px] block text-right">
                                {ins.price}
                              </span>
                            </td>
                            <td className="p-2.5 text-[8px] text-slate-500">{ins.quantity}</td>
                            <td className="p-2.5 text-[8px] text-slate-500 truncate">{ins.delivery_date || 'TBD'}</td>
                            <td className="p-2.5 text-center">
                              {ins.email_body && (
                                <button
                                  onClick={() => {
                                    setSelectedEmail(ins);
                                    setShowEmailModal(true);
                                  }}
                                  className="inline-flex items-center justify-center p-1.5 rounded-lg hover:bg-slate-100 text-slate-500 hover:text-slate-700 transition-colors"
                                  title="View full email"
                                >
                                  <Eye className="w-3.5 h-3.5" />
                                </button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="flex-1 flex flex-col items-center justify-center text-center p-6 space-y-3">
                    <Database className="w-8 h-8 text-slate-300" />
                    <div>
                      <p className="text-xs font-bold text-slate-500">No Offers Extracted Yet</p>
                      <p className="text-[9px] text-slate-400 mt-1 max-w-[180px] leading-relaxed">
                        Supplier replies are being monitored. Click <strong>Refresh</strong> to scan for new responses and extract pricing terms.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Bottom Actions */}
            {selectedJob && (
              <div className="shrink-0 flex gap-2">
                <button 
                  onClick={handleScanInbox}
                  disabled={refreshing}
                  className="flex-1 py-2 bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 text-white rounded-xl font-bold text-xs shadow-md shadow-cyan-600/10 cursor-pointer flex items-center justify-center gap-1.5 active:scale-[0.98] transition-all"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
                  {refreshing ? 'Scanning...' : 'Refresh Insights'}
                </button>

                {selectedJobDetail?.job?.status === 'active' && (
                  <button 
                    onClick={handleCloseCampaign}
                    className="flex-1 py-2 bg-white border border-rose-250 hover:bg-rose-50 text-rose-600 rounded-xl font-bold text-xs shadow-sm cursor-pointer flex items-center justify-center gap-1.5 active:scale-[0.98] transition-all"
                  >
                    <Ban className="w-3.5 h-3.5" />
                    Close & Archive
                  </button>
                )}
              </div>
            )}

          </div>
        </section>

      </main>

      {/* Pinned Bottom Footer Status bar */}
      <footer className="h-[40px] bg-white border-t border-slate-200/80 px-6 flex justify-between items-center shrink-0 z-20 text-[10px] text-slate-500 shadow-inner">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="font-semibold text-slate-600">Database Status: jobs.db Connected</span>
          </div>
          <span className="hidden sm:inline border-l border-slate-200 pl-4">FastAPI port: 8000</span>
        </div>
        <div className="flex items-center gap-2">
          <Database className="w-3.5 h-3.5 text-slate-400" />
          <span className="font-mono text-slate-450 truncate max-w-[280px]">GCS: gs://crystal-supplier-email-data/</span>
        </div>
      </footer>

      {/* Email Modal */}
      {showEmailModal && selectedEmail && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[80vh] flex flex-col">
            {/* Modal Header */}
            <div className="shrink-0 border-b border-slate-200 px-6 py-4 flex justify-between items-start">
              <div className="flex-1">
                <h3 className="text-lg font-bold text-slate-900">Source Email</h3>
                <p className="text-sm text-slate-600 mt-1">
                  <span className="font-semibold">{selectedEmail.supplier}</span>
                  {selectedEmail.contact_person && ` - ${selectedEmail.contact_person}`}
                </p>
              </div>
              <button
                onClick={() => {
                  setShowEmailModal(false);
                  setSelectedEmail(null);
                }}
                className="p-1 hover:bg-slate-100 rounded-lg transition-colors text-slate-500 hover:text-slate-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
              {/* Extracted Data Summary */}
              <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 space-y-2">
                <h4 className="font-semibold text-sm text-emerald-900">Extracted Information</h4>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  {selectedEmail.product && (
                    <div>
                      <span className="text-slate-600 font-medium">Product:</span>
                      <p className="text-slate-800">{selectedEmail.product}</p>
                    </div>
                  )}
                  {selectedEmail.quantity && (
                    <div>
                      <span className="text-slate-600 font-medium">Quantity:</span>
                      <p className="text-slate-800">{selectedEmail.quantity}</p>
                    </div>
                  )}
                  {selectedEmail.price && (
                    <div>
                      <span className="text-slate-600 font-medium">Price:</span>
                      <p className="text-emerald-700 font-bold">{selectedEmail.price}</p>
                    </div>
                  )}
                  {selectedEmail.delivery_date && (
                    <div>
                      <span className="text-slate-600 font-medium">Delivery:</span>
                      <p className="text-slate-800">{selectedEmail.delivery_date}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Full Email */}
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                <h4 className="font-semibold text-sm text-slate-900 mb-3">Full Email Message</h4>
                <div className="bg-white border border-slate-200 rounded p-3 text-sm whitespace-pre-wrap text-slate-700 leading-relaxed max-h-96 overflow-y-auto font-mono text-[12px]">
                  {selectedEmail.email_body}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="shrink-0 border-t border-slate-200 px-6 py-3 flex justify-end">
              <button
                onClick={() => {
                  setShowEmailModal(false);
                  setSelectedEmail(null);
                }}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium rounded-lg transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

export default App;
