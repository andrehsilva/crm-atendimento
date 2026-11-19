export function PageHeader({ titulo, subtitulo }: { titulo: string; subtitulo: string }) {
  return (
    <header className="mb-8">
      <h1 className="text-3xl font-bold tracking-tight">{titulo}</h1>
      <p className="mt-1 text-lg text-muted">{subtitulo}</p>
    </header>
  )
}
