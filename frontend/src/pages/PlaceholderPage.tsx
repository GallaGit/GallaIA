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
      <div className="card empty">Ruta reservada · fuera de alcance de este MVP</div>
    </div>
  )
}
