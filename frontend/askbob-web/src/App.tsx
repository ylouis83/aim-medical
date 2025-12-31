import { useState, useRef, useEffect } from 'react';
import { Send, FileText, User, Activity, Bot, Plus, MessageSquare, Heart, TestTube, Users, Pill } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { chatWithAgent, uploadReport } from './api';
import './index.css';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  memories?: any[];
}

// Memory categorization helper
const categorizeMemory = (mem: any): { label: string; labelZh: string; bgClass: string; icon: any } => {
  const content = (mem.memory || mem.text || '').toLowerCase();
  const sourceType = mem.source_type || mem.metadata?.source_type || '';

  // Check source type first
  if (sourceType === 'report') {
    if (content.includes('reportobservation')) {
      return { label: 'LAB_RESULT', labelZh: '化验结果', bgClass: 'bg-emerald-900/40 text-emerald-300 border-emerald-700/50', icon: TestTube };
    }
    return { label: 'MEDICAL_FACT', labelZh: '医疗事实', bgClass: 'bg-blue-900/40 text-blue-300 border-blue-700/50', icon: Heart };
  }

  // Content-based heuristics
  if (/family|genetic|hereditary|祖传|家族|遗传/.test(content)) {
    return { label: 'FAMILY_HISTORY', labelZh: '家族病史', bgClass: 'bg-orange-900/40 text-orange-300 border-orange-700/50', icon: Users };
  }

  if (/allergy|allergic|过敏/.test(content)) {
    return { label: 'ALLERGY', labelZh: '过敏信息', bgClass: 'bg-red-900/40 text-red-300 border-red-700/50', icon: Heart };
  }

  if (/medication|prescription|药物|处方|用药/.test(content)) {
    return { label: 'PRESCRIPTION', labelZh: '用药记录', bgClass: 'bg-cyan-900/40 text-cyan-300 border-cyan-700/50', icon: Pill };
  }

  if (/symptom|pain|郁闷|抑郁|症状|疼痛|不适/.test(content)) {
    return { label: 'SYMPTOM', labelZh: '症状描述', bgClass: 'bg-yellow-900/40 text-yellow-300 border-yellow-700/50', icon: Activity };
  }

  // Default: Conversation
  return { label: 'CONVERSATION', labelZh: '对话记录', bgClass: 'bg-gray-800/50 text-gray-300 border-gray-700/50', icon: MessageSquare };
};

function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: "您好，刘医生。我是 AskBob 医疗助手。今天有什么可以帮您的吗？",
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [reportText, setReportText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await chatWithAgent(input);
      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.response,
        timestamp: new Date(),
        memories: response.memories
      };
      setMessages(prev => [...prev, botMsg]);
    } catch (err) {
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant',
        content: "抱歉，连接医疗数据库时出现错误。",
        timestamp: new Date()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpload = async () => {
    if (!reportText.trim()) return;
    try {
      await uploadReport(reportText, 'patient_001');
      const successMsg: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: "医疗报告已成功录入并分析。我现在已了解这些新信息。",
        timestamp: new Date()
      };
      setMessages(prev => [...prev, successMsg]);
      setIsUploadOpen(false);
      setReportText('');
    } catch (err) {
      alert("报告上传失败");
    }
  };

  return (
    <div className="flex h-screen bg-[#0f1117] text-[#f0f6fc]">
      {/* Sidebar */}
      <div className="w-64 border-r border-[#30363d] flex flex-col p-4 bg-[#161b22]">
        <div className="flex items-center gap-2 mb-8">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
            <Activity size={18} className="text-white" />
          </div>
          <h1 className="text-xl font-bold font-mono tracking-tight">AskBob<span className="text-[#58a6ff]">Med</span></h1>
        </div>

        <div className="flex-1 space-y-4">
          <div className="bg-[#21262d] p-3 rounded-xl border border-[#30363d]">
            <p className="text-xs text-gray-400 uppercase tracking-wider mb-2">当前患者</p>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center">
                <User size={20} />
              </div>
              <div>
                <p className="font-semibold text-sm">患者 #001</p>
                <p className="text-xs text-blue-400">心内科</p>
              </div>
            </div>
          </div>

          <button
            onClick={() => setIsUploadOpen(true)}
            className="w-full flex items-center gap-2 p-3 rounded-lg hover:bg-[#21262d] transition-colors text-sm text-gray-300"
          >
            <Plus size={16} />
            <span>导入新报告</span>
          </button>
        </div>

        <div className="mt-auto space-y-2">
          <div className="text-[10px] text-gray-500 border-t border-gray-800 pt-2">
            <p className="font-semibold mb-1 text-gray-400">记忆类型说明:</p>
            <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-gray-500"></span> 对话记录</div>
            <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500"></span> 医疗事实</div>
            <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-orange-500"></span> 家族病史</div>
            <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500"></span> 过敏信息</div>
            <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500"></span> 化验结果</div>
            <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-cyan-500"></span> 用药记录</div>
          </div>
          <div className="text-xs text-gray-500 text-center">
            v2.1.0 • 记忆系统已加载
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col relative">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 pb-32">
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-[#58a6ff] to-[#bc8cff] flex-shrink-0 flex items-center justify-center mt-1">
                  <Bot size={16} className="text-white" />
                </div>
              )}

              <div
                className={`max-w-[75%] p-4 rounded-2xl ${msg.role === 'user'
                  ? 'bg-[#1f6feb] text-white rounded-br-sm'
                  : 'bg-[#21262d] border border-[#30363d] rounded-bl-sm'
                  }`}
              >
                <p className="leading-relaxed whitespace-pre-wrap text-sm">{msg.content}</p>

                {/* Structured Memory Context */}
                {msg.memories && msg.memories.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-gray-700/50">
                    <div className="flex items-center gap-2 mb-3">
                      <div className="w-5 h-5 rounded bg-gradient-to-r from-blue-500 to-purple-500 flex items-center justify-center">
                        <Activity size={12} className="text-white" />
                      </div>
                      <span className="text-xs font-bold uppercase tracking-wider text-blue-400">
                        相关记忆 ({msg.memories.length})
                      </span>
                    </div>

                    <div className="space-y-2">
                      {msg.memories.map((mem: any, idx: number) => {
                        const category = categorizeMemory(mem);
                        const IconComponent = category.icon;
                        const displayText = mem.memory || mem.text || JSON.stringify(mem);

                        return (
                          <div
                            key={idx}
                            className={`p-3 rounded-lg border ${category.bgClass} transition-all hover:scale-[1.01]`}
                          >
                            {/* Category Badge */}
                            <div className="flex items-center gap-2 mb-2">
                              <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-black/30">
                                <IconComponent size={10} />
                                <span className="text-[10px] font-bold uppercase tracking-widest">
                                  {category.labelZh}
                                </span>
                              </div>
                              <span className="text-[9px] opacity-40 ml-auto">#{idx + 1}</span>
                            </div>

                            {/* Memory Content */}
                            <p className="text-xs leading-relaxed opacity-90">
                              {displayText.length > 200 ? displayText.slice(0, 200) + '...' : displayText}
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                <span className="text-[10px] opacity-50 mt-2 block">
                  {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>

              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-full bg-gray-600 flex-shrink-0 flex items-center justify-center mt-1">
                  <User size={16} className="text-white" />
                </div>
              )}
            </motion.div>
          ))}
          {isLoading && (
            <div className="flex gap-4">
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-[#58a6ff] to-[#bc8cff] flex-shrink-0 flex items-center justify-center">
                <Bot size={16} className="text-white" />
              </div>
              <div className="bg-[#21262d] p-4 rounded-2xl border border-[#30363d] rounded-bl-sm">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></span>
                  <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '75ms' }}></span>
                  <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-[#0f1117] via-[#0f1117] to-transparent">
          <div className="max-w-4xl mx-auto relative glass-panel p-2 flex items-center gap-2">
            <button
              onClick={() => setIsUploadOpen(true)}
              className="p-2 text-gray-400 hover:text-white transition-colors"
            >
              <FileText size={20} />
            </button>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="询问患者病史、症状，或上传化验报告..."
              className="flex-1 bg-transparent border-none outline-none text-white placeholder-gray-500 px-2"
            />
            <button
              onClick={handleSend}
              disabled={isLoading}
              className="p-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-white transition-colors disabled:opacity-50"
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>

      {/* Upload Modal */}
      <AnimatePresence>
        {isUploadOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
          >
            <motion.div
              initial={{ scale: 0.95 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.95 }}
              className="bg-[#161b22] w-full max-w-lg rounded-xl border border-[#30363d] p-6 shadow-2xl"
            >
              <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                <FileText className="text-blue-400" />
                导入医疗报告
              </h2>
              <textarea
                value={reportText}
                onChange={(e) => setReportText(e.target.value)}
                placeholder="在此粘贴报告内容 (例如: 血常规检查结果...)"
                className="w-full h-48 bg-[#0d1117] border border-[#30363d] rounded-lg p-3 text-sm text-gray-300 focus:border-blue-500 outline-none resize-none"
              />
              <div className="flex justify-end gap-3 mt-4">
                <button
                  onClick={() => setIsUploadOpen(false)}
                  className="px-4 py-2 text-sm text-gray-400 hover:text-white"
                >
                  取消
                </button>
                <button
                  onClick={handleUpload}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold rounded-lg"
                >
                  分析并保存
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default App;
