export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-between font-mono text-sm">
        <h1 className="text-4xl font-bold mb-4">Velox Trading Platform</h1>
        <p className="text-xl mb-8">High-Frequency Algorithmic Trading Platform</p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-8">
          <div className="p-6 border rounded-lg">
            <h2 className="text-2xl font-semibold mb-2">Real-Time Trading</h2>
            <p>Execute multiple trading strategies simultaneously with real-time market data</p>
          </div>

          <div className="p-6 border rounded-lg">
            <h2 className="text-2xl font-semibold mb-2">Risk Management</h2>
            <p>Advanced risk controls with daily loss limits and trailing stop-loss</p>
          </div>

          <div className="p-6 border rounded-lg">
            <h2 className="text-2xl font-semibold mb-2">Live Dashboard</h2>
            <p>Monitor your trading performance with real-time analytics and charts</p>
          </div>
        </div>

        <div className="mt-8">
          <p className="text-sm text-gray-600">
            API Documentation: <a href="http://localhost:8000/docs" className="text-blue-600 hover:underline">http://localhost:8000/docs</a>
          </p>
        </div>
      </div>
    </main>
  )
}
