'use client'

import { Component, ReactNode } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { Button } from './ui/Button'
import { Card, CardContent } from './ui/Card'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background via-surface to-background p-6">
          <Card className="max-w-2xl w-full border-border">
            <CardContent className="p-8 text-center">
              <div className="mb-6">
                <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-4" />
                <h1 className="text-2xl font-bold text-foreground mb-2">
                  Something went wrong
                </h1>
                <p className="text-slate-500 dark:text-slate-400 mb-4">
                  The application encountered an unexpected error
                </p>
              </div>

              {this.state.error && (
                <div className="bg-surface-highlight border border-border rounded-lg p-4 mb-6 text-left">
                  <p className="text-sm font-mono text-red-500 dark:text-red-400 break-all">
                    {this.state.error.message}
                  </p>
                </div>
              )}

              <Button
                variant="primary"
                onClick={this.handleReset}
                icon={<RefreshCw className="w-4 h-4" />}
              >
                Try Again
              </Button>
            </CardContent>
          </Card>
        </div>
      )
    }

    return this.props.children
  }
}
