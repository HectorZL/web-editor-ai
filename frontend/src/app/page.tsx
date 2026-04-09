'use client';

import React, { useState, useEffect } from 'react';
import { 
  Play, Sparkles, History, CheckCircle2, Loader2, Video, 
  Volume2, Type, LayoutGrid, Music, Share2, Info
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import UploadZone from '../components/UploadZone';
import { startProcess, uploadFile, getJobStatus, startAudioProcess, startSubtitlesProcess } from '../lib/api';

type Tab = 'dashboard' | 'audio' | 'video' | 'social' | 'subtitles';

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');
  const [projectName, setProjectName] = useState('');
  const [gameplay, setGameplay] = useState<File | null>(null);
  const [voice, setVoice] = useState<File | null>(null);
  const [music, setMusic] = useState<File | null>(null);
  const [logo, setLogo] = useState<File | null>(null);
  const [script, setScript] = useState('');
  const [language, setLanguage] = useState('auto');
  
  const [isUploading, setIsUploading] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let interval: NodeJS.Timeout | undefined;
    if (jobId && (!status || status.status !== 'COMPLETED' && status.status !== 'FAILED')) {
      interval = setInterval(async () => {
        try {
          const res = await getJobStatus(jobId);
          setStatus(res.data);
          if (res.data.status === 'FAILED') {
            setError(res.data.message || "Error en el pipeline");
          }
        } catch (e) {
          console.error("Error polling status", e);
        }
      }, 2000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [jobId, status]);

  const handleProcess = async () => {
    if (!projectName) {
      alert("Por favor indica un nombre de proyecto para continuar.");
      return;
    }

    setIsUploading(true);
    setError(null);
    try {
      // VALIDACIÓN DE REDUNDANCIA: Evitar subir el mismo archivo para voz y música
      if (voice && music && voice.name === music.name && voice.size === music.size) {
        if (!confirm("Has seleccionado el mismo archivo para VOZ y MÚSICA. ¿Estás seguro de que quieres continuar?")) {
           setIsUploading(false);
           return;
        }
      }

      // Subir archivos solo si han sido seleccionados en esta sesión
      if (activeTab !== 'audio' && gameplay) {
        await uploadFile('gameplay', projectName, gameplay);
      }
      
      if (voice) {
        await uploadFile('voice', projectName, voice);
      }

      if (music) {
        await uploadFile('music', projectName, music);
      }

      if (logo) {
        await uploadFile('logo', projectName, logo);
      }
      
      let res;
      if (activeTab === 'audio') {
        res = await startAudioProcess(projectName);
      } else if (activeTab === 'subtitles') {
        res = await startSubtitlesProcess(projectName, language);
      } else {
        res = await startProcess(projectName);
      }

      setJobId(res.data.job_id);
    } catch (e: any) {
      console.error(e);
      const detail = e.response?.data?.detail || "Error en el servidor. Verifica que el backend esté corriendo.";
      setError(detail);
    } finally {
      setIsUploading(false);
    }
  };

  const tabs = [
    { id: 'dashboard', label: 'DASHBOARD', icon: LayoutGrid },
    { id: 'audio', label: 'AUDIO LAB', icon: Music },
    { id: 'video', label: 'VIDEO STUDIO', icon: Video },
    { id: 'subtitles', label: 'QUICK SUBS', icon: Type },
    { id: 'social', label: 'SOCIAL HUB', icon: Share2 },
  ];

  return (
    <main className="min-h-screen p-6 max-w-7xl mx-auto flex flex-col gap-6 font-sans selection:bg-accent selection:text-black">
      {/* HUD Header */}
      <header className="flex justify-between items-center border-b-2 border-[#2a2a30] pb-4 px-2">
        <div className="flex flex-col">
          <h1 className="text-5xl font-black italic tracking-tighter leading-none hover:text-accent transition-colors cursor-default">
            VIDEOFLOW <span className="text-accent">AI</span>
          </h1>
          <div className="flex items-center gap-3 mt-2">
            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 bg-[#1a1a20] px-2 py-0.5 rounded border border-[#2a2a30]">
              v2.0 PRO PIPELINE
            </span>
            <div className="h-1 w-24 bg-[#2a2a30] rounded-full overflow-hidden">
              <motion.div 
                className="h-full bg-accent" 
                animate={{ width: jobId ? `${status?.progress || 0}%` : '0%' }}
              />
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-6">
          <div className="hidden md:flex flex-col items-end">
            <span className="text-[10px] font-bold text-gray-500 uppercase">System Load</span>
            <span className="text-xs font-mono text-accent">GPU_RTX_3060 :: 5.2GB/6GB</span>
          </div>
          <div className="w-12 h-12 rounded-xl border-2 border-accent flex items-center justify-center animate-pulse shadow-[0_0_15px_rgba(0,255,170,0.3)]">
            <div className="w-6 h-6 bg-accent rounded-sm rotate-45" />
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="flex gap-2 p-1 bg-[#15151a] border border-[#2a2a30] rounded-2xl w-fit">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as Tab)}
            className={`flex items-center gap-3 px-6 py-3 rounded-xl font-black transition-all text-sm uppercase italic tracking-wider ${
              activeTab === tab.id 
                ? 'bg-accent text-black shadow-[0_0_20px_rgba(0,255,170,0.2)]' 
                : 'text-gray-500 hover:text-white hover:bg-[#202025]'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </nav>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 items-stretch">
        <section className="lg:col-span-8 flex flex-col gap-6">
          <AnimatePresence mode="wait">
            {activeTab === 'dashboard' && (
              <motion.div 
                key="dashboard"
                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
                className="flex flex-col gap-6 h-full"
              >
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="glass-card p-6 rounded-3xl border-2 border-[#2a2a30] flex flex-col gap-4">
                    <h3 className="text-xs font-black text-accent uppercase tracking-widest flex items-center gap-2">
                       <Type className="w-3 h-3" /> Kernel Project
                    </h3>
                    <input 
                      type="text" 
                      placeholder="IDENTIFICADOR_PROYECTO"
                      className="w-full bg-[#1a1a20] border-2 border-[#2a2a30] p-4 rounded-xl focus:outline-none focus:border-accent font-mono text-xl"
                      value={projectName}
                      onChange={(e) => setProjectName(e.target.value)}
                    />
                    <p className="text-[10px] text-gray-500 italic mt-1 uppercase">
                      {projectName ? `RE-USANDO ARCHIVOS DE "${projectName}" SI NO SUBES NUEVOS.` : 'TUS ARCHIVOS SE GUARDARÁN CON ESTE NOMBRE.'}
                    </p>
                  </div>
                  <div className="glass-card p-6 rounded-3xl border-2 border-[#2a2a30] flex flex-col justify-center">
                    <div className="flex justify-between items-center px-4">
                      <div className="flex flex-col">
                        <span className="text-[10px] font-bold text-gray-500">Auto-Detect Lang</span>
                        <span className="text-sm font-black text-white">ENABLED</span>
                      </div>
                      <div className="w-12 h-6 bg-accent rounded-full p-1 cursor-pointer">
                        <div className="w-4 h-4 bg-black rounded-full" />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1">
                  <div className="glass-card p-6 rounded-3xl border-2 border-[#2a2a30] flex flex-col gap-4">
                    <h3 className="text-xs font-black text-accent uppercase tracking-widest">Gameplay Source</h3>
                    <UploadZone label="DROP MP4/MOV" type="video" onFileSelect={setGameplay} isUploaded={!!gameplay} />
                  </div>
                  <div className="glass-card p-6 rounded-3xl border-2 border-[#2a2a30] flex flex-col gap-4">
                    <h3 className="text-xs font-black text-accent uppercase tracking-widest">Voice Core</h3>
                    <UploadZone label="DROP MP3/WAV" type="audio" onFileSelect={setVoice} isUploaded={!!voice} />
                  </div>
                  <div className="glass-card p-6 rounded-3xl border-2 border-[#2a2a30] flex flex-col gap-4">
                    <h3 className="text-xs font-black text-accent uppercase tracking-widest">Background Music</h3>
                    <UploadZone label="DROP MP3 (OPTIONAL)" type="audio" onFileSelect={setMusic} isUploaded={!!music} />
                  </div>
                  <div className="glass-card p-6 rounded-3xl border-2 border-[#2a2a30] flex flex-col gap-4">
                    <h3 className="text-xs font-black text-gray-500 uppercase tracking-widest flex items-center gap-2">
                      <Sparkles className="w-3 h-3" /> Logo / Watermark
                    </h3>
                    <UploadZone label="DROP PNG/JPG" type="image" onFileSelect={setLogo} isUploaded={!!logo} />
                  </div>
                </div>
              </motion.div>
            )}

            {activeTab === 'audio' && (
              <motion.div 
                key="audio"
                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
                className="flex flex-col gap-6"
              >
                <div className="glass-card p-8 rounded-3xl border-2 border-[#2a2a30] flex flex-col gap-8">
                  <div className="flex justify-between items-start">
                    <div>
                      <h2 className="text-3xl font-black italic text-white uppercase tracking-tighter">Audio Lab</h2>
                      <p className="text-gray-500 text-sm mt-1">Configure ducking and background atmos.</p>
                    </div>
                    <Music className="w-10 h-10 text-accent" />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="flex flex-col gap-4">
                       <h3 className="text-xs font-black text-gray-400 uppercase">Voice Source (My Audio)</h3>
                       <UploadZone label="DROP VOICE (.mp3/.wav)" type="audio" onFileSelect={setVoice} isUploaded={!!voice} />
                    </div>
                    <div className="flex flex-col gap-4">
                       <h3 className="text-xs font-black text-gray-400 uppercase">Atmosphere File (My Song)</h3>
                       <UploadZone label="DROP MUSIC (.mp3)" type="audio" onFileSelect={setMusic} isUploaded={!!music} />
                    </div>
                  </div>

                  <div className="p-6 bg-[#1a1a20] border-2 border-[#2a2a30] rounded-2xl">
                    <div className="flex justify-between mb-4">
                      <span className="text-xs font-bold text-accent">DUCKING STRENGTH</span>
                      <span className="text-xs font-mono">-20dB</span>
                    </div>
                    <div className="h-2 w-full bg-[#15151a] rounded-full p-0.5 border border-[#2a2a30]">
                       <div className="h-full w-3/4 bg-accent rounded-full shadow-[0_0_10px_rgba(0,255,170,0.5)]" />
                    </div>
                    <p className="text-[10px] text-gray-600 mt-4 italic uppercase">Music will automatically drop when voice frequencies are detected.</p>
                  </div>
                </div>
              </motion.div>
            )}

            {activeTab === 'video' && (
              <motion.div 
                key="video"
                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
                className="flex flex-col gap-6"
              >
                 <div className="glass-card p-8 rounded-3xl border-2 border-[#2a2a30] min-h-100 flex flex-col justify-center items-center text-center gap-4">
                    <div className="w-20 h-20 rounded-full border-4 border-[#2a2a30] border-t-accent animate-spin" />
                    <h2 className="text-2xl font-black italic uppercase">Analyzing Cinematic Flow...</h2>
                    <p className="text-gray-500 max-w-sm">AI is scanning gameplay for high-action scenes to match with script points.</p>
                 </div>
              </motion.div>
            )}

            {activeTab === 'subtitles' && (
              <motion.div 
                key="subtitles"
                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
                className="flex flex-col gap-6"
              >
                <div className="glass-card p-8 rounded-3xl border-2 border-[#2a2a30] flex flex-col gap-8">
                  <div className="flex justify-between items-start">
                    <div>
                      <h2 className="text-3xl font-black italic text-white uppercase tracking-tighter">Quick Subtitles</h2>
                      <p className="text-gray-500 text-sm mt-1">Burn AI-generated subtitles instantly. Auto-Language enabled.</p>
                    </div>
                    <div className="flex flex-col items-end">
                      <Type className="w-10 h-10 text-accent mb-2" />
                      <span className="text-[10px] font-black text-accent bg-accent/10 px-2 py-0.5 rounded border border-accent/20">WHISPER MEDIUM</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 gap-6">
                    <div className="glass-card p-6 rounded-3xl border-2 border-[#2a2a30] flex flex-col gap-4">
                      <h3 className="text-xs font-black text-accent uppercase tracking-widest flex items-center gap-2">
                        <Type className="w-3 h-3" /> Project Name
                      </h3>
                      <input 
                        type="text" 
                        placeholder="NOMBRE_DEL_VIDEO"
                        className="w-full bg-[#1a1a20] border-2 border-[#2a2a30] p-4 rounded-xl focus:outline-none focus:border-accent font-mono text-xl"
                        value={projectName}
                        onChange={(e) => setProjectName(e.target.value)}
                      />
                    </div>
                    
                    <div className="flex flex-col gap-4">
                      <h3 className="text-xs font-black text-gray-400 uppercase">Input Video File</h3>
                      <UploadZone label="DROP VIDEO (.mp4/.mov)" type="video" onFileSelect={setGameplay} isUploaded={!!gameplay} />
                    </div>

                    <div className="glass-card p-6 rounded-3xl border-2 border-[#2a2a30] flex flex-col gap-4">
                      <h3 className="text-xs font-black text-accent uppercase tracking-widest flex items-center gap-2">
                        <Type className="w-3 h-3" /> Target Language
                      </h3>
                      <select 
                        className="w-full bg-[#1a1a20] border-2 border-[#2a2a30] p-4 rounded-xl focus:outline-none focus:border-accent font-mono text-xl text-white appearance-none cursor-pointer"
                        value={language}
                        onChange={(e) => setLanguage(e.target.value)}
                      >
                        <option value="auto">AUTO-DETECT (IA)</option>
                        <option value="en">ENGLISH (UK/US)</option>
                        <option value="es">ESPAÑOL (ES/LATAM)</option>
                        <option value="fr">FRANÇAIS</option>
                        <option value="de">DEUTSCH</option>
                        <option value="pt">PORTUGUÊS</option>
                        <option value="it">ITALIANO</option>
                      </select>
                      <p className="text-[10px] text-gray-500 italic mt-1 uppercase">
                        FORZAR EL IDIOMA EVITA ERRORES DE DETECCIÓN EN VIDEOS CON RUIDO.
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 bg-[#1a1a20] border border-[#2a2a30] rounded-2xl flex items-center gap-4">
                      <div className="w-10 h-10 rounded-lg bg-white/5 flex items-center justify-center">
                        <div className="w-4 h-4 bg-white rounded-sm" />
                      </div>
                      <div>
                        <p className="text-[10px] font-black text-gray-500 uppercase">Text Color</p>
                        <p className="text-xs font-bold text-white">OPTIMIZED WHITE</p>
                      </div>
                    </div>
                    <div className="p-4 bg-[#1a1a20] border border-[#2a2a30] rounded-2xl flex items-center gap-4">
                      <div className="w-10 h-10 rounded-lg bg-white/5 flex items-center justify-center">
                        <div className="w-4 h-4 bg-[#cccccc] rounded-sm" />
                      </div>
                      <div>
                        <p className="text-[10px] font-black text-gray-500 uppercase">Highlight</p>
                        <p className="text-xs font-bold text-white">SOFT GRAY (PRO)</p>
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}

            {activeTab === 'social' && (
              <motion.div 
                key="social"
                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
                className="flex flex-col gap-6"
              >
                {error && (
                  <motion.div 
                    initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
                    className="p-4 bg-red-500/10 border-2 border-red-500/50 rounded-2xl text-red-500 text-sm font-black uppercase italic"
                  >
                    ALERTA: {error}
                  </motion.div>
                )}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="glass-card p-8 rounded-3xl border-2 border-[#2a2a30] flex flex-col gap-6">
                    <h3 className="text-xl font-black italic uppercase text-accent">TikTok / Reels Reframe</h3>
                    <div className="aspect-video md:aspect-9/16 bg-black rounded-2xl border-4 border-[#2a2a30] relative overflow-hidden flex items-center justify-center group">
                       <span className="text-[10px] font-black text-[#2a2a30] uppercase">9:16 Preview Matrix</span>
                       <div className="absolute bottom-12 left-0 right-0 px-4">
                          <div className="bg-[#faff00] p-1 text-black font-black text-center text-xs shadow-[4px_4px_0px_#00ff41]">
                            DYNAMIC SUBTITLES ACTIVE
                          </div>
                       </div>
                    </div>
                    <div className="flex flex-col gap-3">
                       <div className="flex justify-between items-center text-[10px] font-black uppercase text-gray-500">
                          <span>Subtitle Style</span>
                          <span className="text-[#faff00]">HIGH SATURATION</span>
                       </div>
                       <div className="flex gap-2">
                          <div className="h-2 flex-1 bg-[#faff00] rounded-full" />
                          <div className="h-2 flex-1 bg-[#00ff41] rounded-full" />
                          <div className="h-2 flex-1 bg-white rounded-full" />
                       </div>
                    </div>
                  </div>

                  <div className="flex flex-col gap-6">
                    <div className="glass-card p-6 rounded-3xl border-2 border-[#2a2a30] flex flex-col gap-4">
                      <h3 className="text-xs font-black text-gray-500 uppercase tracking-widest">Platform Presets</h3>
                      <div className="grid grid-cols-2 gap-3">
                         <button className="bg-[#1a1a20] border-2 border-accent text-accent p-4 rounded-xl font-black text-xs">TIKTOK / REELS</button>
                         <button className="bg-[#1a1a20] border-2 border-[#2a2a30] text-gray-500 p-4 rounded-xl font-black text-xs hover:border-gray-500">YOUTUBE MAIN</button>
                      </div>
                    </div>
                    
                    <div className="glass-card p-6 rounded-3xl border-2 border-[#2a2a30] flex-1">
                       <h3 className="text-xs font-black text-gray-500 uppercase tracking-widest mb-4">Export Queue</h3>
                       <div className="space-y-3">
                          {[1,2,3,4].map(i => (
                            <div key={i} className="flex items-center gap-3 p-3 bg-[#15151a] border border-[#2a2a30] rounded-xl opacity-40">
                               <div className="w-2 h-2 rounded-full bg-gray-600" />
                               <span className="text-[10px] font-mono text-gray-500">JOB_ID_{i}0293_PENDING</span>
                            </div>
                          ))}
                       </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {(activeTab === 'dashboard' || activeTab === 'audio' || activeTab === 'subtitles') && (
            <button 
              onClick={handleProcess}
              disabled={isUploading || status?.status === 'PROCESSING'}
              className={`group relative overflow-hidden py-8 rounded-3xl font-black text-2xl transition-all mt-auto ${
                isUploading || status?.status === 'PROCESSING'
                  ? 'bg-[#1a1a20] text-gray-700 cursor-not-allowed border-2 border-[#2a2a30]'
                  : 'bg-accent text-black hover:scale-[1.01] active:scale-[0.99] shadow-[0_10px_30px_rgba(0,255,170,0.2)]'
              }`}
            >
                <div className="relative z-10 flex items-center justify-center gap-4 uppercase italic tracking-tighter">
                {(isUploading || status?.status === 'PROCESSING') ? <Loader2 className="w-8 h-8 animate-spin" /> : <Play className="w-8 h-8 fill-black" />}
                {activeTab === 'audio' ? "MIX & PROCESS AUDIO" : activeTab === 'subtitles' ? "Ignite Subtitles" : "Ignite Pipeline Sequence"}
                </div>
                <motion.div 
                initial={{ x: '-100%' }}
                animate={status?.status === 'PROCESSING' ? { x: '100%' } : { x: '-100%' }}
                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                className="absolute inset-0 bg-white/10 skew-x-12"
                />
            </button>
          )}
        </section>

        {/* HUD: RIGHT SIDEBAR */}
        <aside className="lg:col-span-4 flex flex-col gap-6">
          <div className="glass-card p-6 rounded-3xl border-2 border-accent bg-accent/5 flex flex-col gap-6 relative overflow-hidden">
            <div className="flex items-center justify-between">
               <h2 className="text-xl font-black italic flex items-center gap-3">
                {status?.status === 'PROCESSING' ? <Loader2 className="w-5 h-5 animate-spin" /> : <Info className="w-5 h-5" />}
                STATUS FEED
              </h2>
              <span className="bg-accent text-black text-[10px] font-black px-2 py-0.5 rounded uppercase">Realtime</span>
            </div>
            
            <div className="flex flex-col gap-4">
              <div className="flex justify-between items-center bg-black/40 p-4 rounded-2xl border border-white/5">
                <span className="text-xs font-bold text-gray-400 uppercase tracking-widest">Global Process</span>
                <span className="text-2xl font-black text-accent">{status?.progress || 0}%</span>
              </div>
              
              <div className="space-y-2 max-h-64 overflow-y-auto font-mono scrollbar-hide">
                {jobId ? (
                  <div className="p-4 bg-black/40 rounded-2xl border border-accent/20">
                    <p className="text-[10px] text-accent font-black uppercase mb-2 animate-pulse tracking-widest">{">>>"} SYS_LOG.active</p>
                    <p className="text-sm text-gray-300 leading-relaxed uppercase">{status?.message}</p>
                  </div>
                ) : (
                  <p className="text-xs text-gray-600 italic text-center p-8">Esperando flujo de datos...</p>
                )}
              </div>

                  {status?.status === 'COMPLETED' && (
                    <motion.a 
                      initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
                      href={`http://localhost:8000${status.result_url}`}
                      download
                      className="bg-white text-black p-5 rounded-2xl font-black uppercase flex items-center justify-center gap-3 hover:bg-accent transition-colors shadow-xl"
                    >
                      <CheckCircle2 className="w-5 h-5" /> 
                      {status.result_url?.endsWith('.mp3') ? 'RECOGER AUDIO MEZCLADO' : 'RECOGER VIDEO FINAL'}
                    </motion.a>
                  )}
            </div>
          </div>

          <div className="glass-card p-6 rounded-3xl border-2 border-[#2a2a30] flex flex-col gap-4">
            <h2 className="text-xs font-black text-gray-500 uppercase tracking-widest flex items-center gap-2">
              <History className="w-4 h-4" /> KERNEL HISTORY
            </h2>
            <div className="flex flex-col gap-3">
               <div className="p-4 bg-[#1a1a20] rounded-2xl border border-[#2a2a30] flex justify-between items-center opacity-50 grayscale">
                  <div className="flex flex-col">
                    <span className="text-[10px] font-black text-white">RESEÑA_MISIDE_FINAL</span>
                    <span className="text-[8px] font-mono text-gray-500 uppercase">2026-04-05_09:12AM</span>
                  </div>
                  <Share2 className="w-4 h-4 text-gray-600" />
               </div>
            </div>
          </div>
        </aside>
      </div>
    </main>
  );
}
