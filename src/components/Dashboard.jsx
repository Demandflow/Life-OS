import { useState } from 'react'
import ReflectionForm from './ReflectionForm'
import DailyOverview from './DailyOverview'

function Dashboard() {
  const [activeReport, setActiveReport] = useState('morning') // or 'evening'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Daily Reflection</h1>
        <div className="flex space-x-4">
          <button
            onClick={() => setActiveReport('morning')}
            className={`px-4 py-2 rounded-lg ${
              activeReport === 'morning'
                ? 'bg-primary-500 text-white'
                : 'bg-gray-200 text-gray-700'
            }`}
          >
            Morning Report
          </button>
          <button
            onClick={() => setActiveReport('evening')}
            className={`px-4 py-2 rounded-lg ${
              activeReport === 'evening'
                ? 'bg-primary-500 text-white'
                : 'bg-gray-200 text-gray-700'
            }`}
          >
            Evening Report
          </button>
        </div>
      </div>

      <DailyOverview type={activeReport} />
      <ReflectionForm type={activeReport} />
    </div>
  )
}

export default Dashboard 