import { useEffect } from 'react';
import { ReactFlowProvider } from '@xyflow/react';
import Canvas from './components/Canvas';
import Sidebar from './components/Sidebar';
import Monitor from './components/Monitor';
import AgentConfigModal from './components/AgentConfigModal';
import TaskSubmitModal from './components/TaskSubmitModal';
import { useStore } from './store';

export default function App() {
  const loadAgents = useStore(s => s.loadAgents);
  const connectWs = useStore(s => s.connectWs);

  useEffect(() => {
    loadAgents();
    connectWs();
  }, [loadAgents, connectWs]);

  return (
    <div className="h-screen flex flex-col">
      <div className="flex flex-1 min-h-0">
        <Sidebar />
        <ReactFlowProvider>
          <Canvas />
        </ReactFlowProvider>
        <Monitor />
      </div>
      <AgentConfigModal />
      <TaskSubmitModal />
    </div>
  );
}
