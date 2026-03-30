import { ReactFlowProvider } from '@xyflow/react';
import Canvas from './components/Canvas';
import Sidebar from './components/Sidebar';
import Monitor from './components/Monitor';
import AgentConfigModal from './components/AgentConfigModal';
import TaskSubmitModal from './components/TaskSubmitModal';
import Landing from './components/Landing';
import { useStore } from './store';

export default function App() {
  const view = useStore(s => s.view);

  if (view === 'landing') {
    return <Landing />;
  }

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
