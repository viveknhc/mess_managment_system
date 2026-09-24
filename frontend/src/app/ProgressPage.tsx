import { useState } from "react"
import { modules, type Module, type ModuleStatus } from "./progress"

const statusConfig: Record<
  ModuleStatus,
  { label: string; bg: string; text: string; dot: string; border: string }
> = {
  completed: {
    label: "Completed",
    bg: "bg-emerald-50",
    text: "text-emerald-700",
    dot: "bg-emerald-500",
    border: "border-emerald-200",
  },
  in_progress: {
    label: "In Progress",
    bg: "bg-amber-50",
    text: "text-amber-700",
    dot: "bg-amber-500",
    border: "border-amber-200",
  },
  not_started: {
    label: "Not Started",
    bg: "bg-gray-50",
    text: "text-gray-500",
    dot: "bg-gray-300",
    border: "border-gray-200",
  },
}

function ProgressBar({ completed, total }: { completed: number; total: number }) {
  const pct = total > 0 ? (completed / total) * 100 : 0
  return (
    <div className="h-2 w-full rounded-full bg-gray-200">
      <div
        className={`h-2 rounded-full transition-all duration-500 ${
          pct === 100
            ? "bg-emerald-500"
            : pct > 0
              ? "bg-amber-500"
              : "bg-gray-300"
        }`}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

function StatusBadge({ status }: { status: ModuleStatus }) {
  const c = statusConfig[status]
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${c.bg} ${c.text}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  )
}

function ModuleCard({
  module,
  isExpanded,
  onToggle,
}: {
  module: Module
  isExpanded: boolean
  onToggle: () => void
}) {
  const c = statusConfig[module.status]
  const pct =
    module.totalTasks > 0
      ? Math.round((module.completedTasks / module.totalTasks) * 100)
      : 0

  return (
    <div
      className={`rounded-xl border ${c.border} bg-white shadow-sm transition-shadow hover:shadow-md`}
    >
      <button
        onClick={onToggle}
        className="flex w-full items-start gap-4 p-5 text-left"
      >
        {/* Module number */}
        <div
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-sm font-bold ${
            module.status === "completed"
              ? "bg-emerald-100 text-emerald-700"
              : module.status === "in_progress"
                ? "bg-amber-100 text-amber-700"
                : "bg-gray-100 text-gray-400"
          }`}
        >
          {module.status === "completed" ? (
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          ) : (
            module.id
          )}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-gray-900">{module.name}</h3>
            <StatusBadge status={module.status} />
          </div>
          <p className="mt-0.5 text-xs text-gray-500">{module.description}</p>
          <div className="mt-3 flex items-center gap-3">
            <div className="flex-1">
              <ProgressBar completed={module.completedTasks} total={module.totalTasks} />
            </div>
            <span className="shrink-0 text-xs font-medium text-gray-500">
              {module.completedTasks}/{module.totalTasks} ({pct}%)
            </span>
          </div>
        </div>

        {/* Expand icon */}
        <svg
          className={`mt-1 h-4 w-4 shrink-0 text-gray-400 transition-transform ${isExpanded ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Task list */}
      {isExpanded && (
        <div className="border-t border-gray-100 px-5 py-3">
          <ul className="space-y-1.5">
            {module.tasks.map((task) => (
              <li key={task.id} className="flex items-center gap-2.5 text-sm">
                {task.done ? (
                  <svg className="h-4 w-4 shrink-0 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                ) : (
                  <div className="h-4 w-4 shrink-0 rounded-full border-2 border-gray-300" />
                )}
                <span className="font-mono text-xs text-gray-400">{task.id}</span>
                <span className={task.done ? "text-gray-400 line-through" : "text-gray-700"}>
                  {task.title}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export function ProgressPage() {
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const totalTasks = modules.reduce((s, m) => s + m.totalTasks, 0)
  const totalDone = modules.reduce((s, m) => s + m.completedTasks, 0)
  const overallPct = Math.round((totalDone / totalTasks) * 100)

  const completedCount = modules.filter((m) => m.status === "completed").length
  const inProgressCount = modules.filter((m) => m.status === "in_progress").length
  const notStartedCount = modules.filter((m) => m.status === "not_started").length

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          Mess Management System
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          MVP Development Progress Tracker
        </p>
      </div>

      {/* Overall stats */}
      <div className="mb-8 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-end justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">Overall Progress</p>
            <p className="mt-1 text-3xl font-bold text-gray-900">{overallPct}%</p>
          </div>
          <p className="text-sm text-gray-500">
            {totalDone} of {totalTasks} tasks
          </p>
        </div>
        <div className="mt-4">
          <div className="h-3 w-full overflow-hidden rounded-full bg-gray-200">
            <div
              className="h-3 rounded-full bg-emerald-500 transition-all duration-700"
              style={{ width: `${overallPct}%` }}
            />
          </div>
        </div>

        {/* Summary chips */}
        <div className="mt-5 flex gap-4">
          <div className="flex items-center gap-2 rounded-lg bg-emerald-50 px-3 py-2">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
            <span className="text-sm font-medium text-emerald-700">
              {completedCount} Completed
            </span>
          </div>
          <div className="flex items-center gap-2 rounded-lg bg-amber-50 px-3 py-2">
            <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />
            <span className="text-sm font-medium text-amber-700">
              {inProgressCount} In Progress
            </span>
          </div>
          <div className="flex items-center gap-2 rounded-lg bg-gray-100 px-3 py-2">
            <span className="h-2.5 w-2.5 rounded-full bg-gray-400" />
            <span className="text-sm font-medium text-gray-600">
              {notStartedCount} Not Started
            </span>
          </div>
        </div>
      </div>

      {/* Module list */}
      <div className="space-y-3">
        {modules.map((m) => (
          <ModuleCard
            key={m.id}
            module={m}
            isExpanded={expandedId === m.id}
            onToggle={() => setExpandedId(expandedId === m.id ? null : m.id)}
          />
        ))}
      </div>

      {/* Footer */}
      <p className="mt-8 text-center text-xs text-gray-400">
        Source of truth: docs/tasks.md — {totalTasks} tasks across {modules.length} modules
      </p>
    </div>
  )
}
