type LevelSliderProps = {
  value: number
  onChange: (level: number) => void
}

export default function LevelSlider({ value, onChange }: LevelSliderProps) {
  return (
    <section aria-labelledby="level-heading" className="level-panel">
      <div className="level-heading-row">
        <div>
          <p className="eyebrow">Progression</p>
          <h2 id="level-heading">Character level</h2>
        </div>
        <output className="level-current" htmlFor="character-level" aria-live="polite">
          {value}
        </output>
      </div>
      <label className="sr-only" htmlFor="character-level">
        Character level
      </label>
      <input
        id="character-level"
        aria-label="Character level"
        className="level-range"
        type="range"
        min={1}
        max={60}
        step={1}
        value={value}
        onChange={(event) => onChange(Number(event.currentTarget.value))}
      />
      <div className="level-range-labels" aria-hidden="true">
        <span>1</span>
        <span>60</span>
      </div>
    </section>
  )
}
