import { useState } from 'react'
import ImageUpload from './ImageUpload'

function ReflectionForm({ type }) {
  const [formData, setFormData] = useState({
    reflection: '',
    priorities: '',
    challenges: '',
    images: []
  })

  const questions = {
    morning: [
      { id: 'priorities', label: 'What are your top priorities for today?' },
      { id: 'intention', label: 'What is your intention for the day?' }
    ],
    evening: [
      { id: 'reflection', label: 'How did your day go?' },
      { id: 'challenges', label: 'What challenges did you face?' },
      { id: 'tomorrow', label: 'What do you want to focus on tomorrow?' }
    ]
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    // TODO: Implement API call to save reflection
    console.log('Submitting reflection:', formData)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6 bg-white p-6 rounded-lg shadow">
      {questions[type].map((question) => (
        <div key={question.id} className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">
            {question.label}
          </label>
          <textarea
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
            rows="3"
            value={formData[question.id] || ''}
            onChange={(e) =>
              setFormData({ ...formData, [question.id]: e.target.value })
            }
          />
        </div>
      ))}

      <ImageUpload
        onImagesSelected={(images) => setFormData({ ...formData, images })}
      />

      <button
        type="submit"
        className="w-full bg-primary-500 text-white py-2 px-4 rounded-md hover:bg-primary-600"
      >
        Save Reflection
      </button>
    </form>
  )
}

export default ReflectionForm 