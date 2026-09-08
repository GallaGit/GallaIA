type Props = { title: string; blurb: string }

export default function PlaceholderPage({ title, blurb }: Props) {
  return (
    <div>
      <div className="page-header">
        <div>
          <h2>{title}</h2>
          <p>{blurb}</p>
        </div>
      </div>
      <div className="card empty">
        <span className="pill-coral pill">atelier</span> Próximamente
      </div>
    </div>
  )
}
