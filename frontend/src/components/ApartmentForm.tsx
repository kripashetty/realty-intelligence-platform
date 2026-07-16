import { useForm } from 'react-hook-form'
import type { ApartmentRequest } from '../services/api'

const AMENITIES = ['balcony', 'parking', 'elevator', 'furnished', 'garden', 'cellar'] as const

interface FormValues {
  address: string
  size_m2: number
  rooms: number
  floor?: number
  amenities: string[]
}

interface Props {
  onSubmit: (data: ApartmentRequest) => void
  isLoading: boolean
}

export function ApartmentForm({ onSubmit, isLoading }: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ defaultValues: { amenities: [] } })

  function handleFormSubmit(values: FormValues) {
    onSubmit({
      address: values.address,
      size_m2: Number(values.size_m2),
      rooms: Number(values.rooms),
      floor: values.floor ? Number(values.floor) : undefined,
      amenities: values.amenities.length ? values.amenities : undefined,
    })
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="apartment-form" noValidate>
      <div className="form-field">
        <label htmlFor="address">Address</label>
        <input
          id="address"
          type="text"
          {...register('address', { required: 'Address is required' })}
        />
        {errors.address && <span className="form-error">{errors.address.message}</span>}
      </div>

      <div className="form-field">
        <label htmlFor="size_m2">Size (m²)</label>
        <input
          id="size_m2"
          type="number"
          step="0.5"
          {...register('size_m2', {
            required: 'Size is required',
            min: { value: 5, message: 'Must be at least 5 m²' },
            max: { value: 1000, message: 'Must be at most 1000 m²' },
          })}
        />
        {errors.size_m2 && <span className="form-error">{errors.size_m2.message}</span>}
      </div>

      <div className="form-field">
        <label htmlFor="rooms">Rooms</label>
        <input
          id="rooms"
          type="number"
          step="0.5"
          {...register('rooms', {
            required: 'Rooms is required',
            min: { value: 0.5, message: 'Must be at least 0.5' },
            max: { value: 20, message: 'Must be at most 20' },
          })}
        />
        {errors.rooms && <span className="form-error">{errors.rooms.message}</span>}
      </div>

      <div className="form-field">
        <label htmlFor="floor">Floor (optional)</label>
        <input
          id="floor"
          type="number"
          {...register('floor', {
            min: { value: 0, message: 'Floor must be ≥ 0' },
            max: { value: 50, message: 'Floor must be ≤ 50' },
          })}
        />
        {errors.floor && <span className="form-error">{errors.floor.message}</span>}
      </div>

      <fieldset className="form-field">
        <legend>Amenities</legend>
        {AMENITIES.map((a) => (
          <label key={a} className="checkbox-label">
            <input type="checkbox" value={a} {...register('amenities')} />
            {a.charAt(0).toUpperCase() + a.slice(1)}
          </label>
        ))}
      </fieldset>

      <button type="submit" disabled={isLoading}>
        {isLoading ? 'Loading…' : 'Get Recommendation'}
      </button>
    </form>
  )
}
