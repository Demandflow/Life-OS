import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'

function ImageUpload({ onImagesSelected }) {
  const onDrop = useCallback(
    (acceptedFiles) => {
      // Convert files to array of objects with preview URLs
      const images = acceptedFiles.map((file) =>
        Object.assign(file, {
          preview: URL.createObjectURL(file)
        })
      )
      onImagesSelected(images)
    },
    [onImagesSelected]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png']
    }
  })

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer
        ${isDragActive ? 'border-primary-500 bg-primary-50' : 'border-gray-300'}`}
    >
      <input {...getInputProps()} />
      <p className="text-gray-600">
        {isDragActive
          ? 'Drop the images here...'
          : 'Drag & drop images here, or click to select files'}
      </p>
    </div>
  )
}

export default ImageUpload 