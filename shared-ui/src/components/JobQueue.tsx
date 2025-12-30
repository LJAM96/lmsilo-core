import React from 'react'
import { CheckCircle2, XCircle, Clock, Loader2, Trash2, AlertCircle } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

export type QueueItemStatus = 
  | 'pending' 
  | 'queued' 
  | 'processing' 
  | 'completed' 
  | 'failed' 
  | 'cancelled';

export interface QueueItemData {
  id: string
  title: string
  subtitle?: string
  status: QueueItemStatus | string
  progress?: number
  createdAt?: string | Date
  thumbnailUrl?: string
  stage?: string
  error?: string
  icon?: React.ElementType
}

export interface JobQueueProps {
  items: QueueItemData[]
  onSelect?: (video: QueueItemData) => void
  selectedId?: string
  onDelete?: (id: string) => void
  onAction?: (action: string, item: QueueItemData) => void
  className?: string
  emptyMessage?: string
  renderActions?: (item: QueueItemData) => React.ReactNode
}

export function JobQueue({ 
  items, 
  onSelect, 
  selectedId, 
  onDelete, 
  renderActions,
  className = '',
  emptyMessage = "No items in queue"
}: JobQueueProps) {

  if (items.length === 0) {
    return (
      <div className={`text-center py-12 border-2 border-dashed border-cream-200 dark:border-dark-100 rounded-2xl bg-cream-50/50 dark:bg-dark-200/50 ${className}`}>
        <p className="text-surface-500 font-medium">{emptyMessage}</p>
      </div>
    )
  }

  return (
    <div className={`space-y-3 ${className}`}>
      {items.map((item) => (
        <QueueItem 
          key={item.id} 
          item={item} 
          isSelected={selectedId === item.id}
          onClick={() => onSelect?.(item)}
          onDelete={onDelete ? () => onDelete(item.id) : undefined}
          renderActions={renderActions}
        />
      ))}
    </div>
  )
}

function QueueItem({ 
  item, 
  isSelected, 
  onClick, 
  onDelete,
  renderActions
}: { 
  item: QueueItemData
  isSelected: boolean
  onClick?: () => void
  onDelete?: () => void
  renderActions?: (item: QueueItemData) => React.ReactNode
}) {
  const config = getStatusConfig(item.status)
  const isProcessing = ['processing', 'extracting', 'transcribing', 'detecting', 'translating'].includes(item.status.toLowerCase())

  // Default Icon if none provided
  const Icon = item.icon || config.icon

  return (
    <div
      onClick={onClick}
      className={`
        group relative overflow-hidden rounded-xl border p-4 transition-all
        ${onClick ? 'cursor-pointer' : ''}
        ${isSelected
          ? 'bg-olive-50 dark:bg-olive-900/10 border-olive-500 dark:border-olive-400 shadow-md ring-1 ring-olive-500/20'
          : 'bg-white dark:bg-dark-200 border-cream-200 dark:border-dark-100 hover:bg-cream-50 dark:hover:bg-dark-100 hover:shadow-sm'
        }
      `}
    >
      <div className="flex items-center gap-4">
        {/* Icon / Thumbnail Box */}
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 ${config.bgColor} overflow-hidden transition-colors`}>
          {item.thumbnailUrl ? (
            <img 
              src={item.thumbnailUrl} 
              alt="" 
              className="w-full h-full object-cover opacity-90"
            />
          ) : (
            <Icon className={`w-6 h-6 ${config.iconColor}`} />
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <p className={`font-medium truncate ${isSelected ? 'text-olive-900 dark:text-olive-100' : 'text-surface-800 dark:text-cream-100'}`}>
              {item.title}
            </p>
            
            {/* Status Pill */}
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${config.pillClass}`}>
              <config.icon className="w-3 h-3" />
              {item.stage || formatStatus(item.status)}
            </span>
          </div>

          <div className="flex items-center gap-3 text-sm text-surface-500 dark:text-surface-400">
            {item.subtitle && <span>{item.subtitle}</span>}
            {item.createdAt && (
               <>
                <span className="text-surface-300">•</span>
                <span>{formatDistanceToNow(new Date(item.createdAt), { addSuffix: true })}</span>
               </>
            )}
            {item.error && (
               <span className="text-red-500 flex items-center gap-1">
                 <AlertCircle className="w-3 h-3" />
                 {item.error}
               </span>
            )}
          </div>

          {/* Progress Bar */}
          {(isProcessing || (typeof item.progress === 'number' && item.progress < 100)) && (
             <div className="mt-3">
               <div className="flex justify-between text-xs mb-1 text-surface-500">
                  <span>Processing...</span>
                  <span className="font-medium">{item.progress ? Math.round(item.progress) : 0}%</span>
               </div>
               <div className="h-1.5 w-full bg-cream-200 dark:bg-dark-50 rounded-full overflow-hidden">
                   <div 
                      className={`h-full rounded-full transition-all duration-300 ${config.barColor} ${!item.progress ? 'animate-pulse w-2/3' : ''}`}
                      style={{ width: item.progress ? `${item.progress}%` : undefined }}
                   />
               </div>
             </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
           {renderActions?.(item)}
           
           {onDelete && (
             <button
                onClick={(e) => {
                  e.stopPropagation()
                  onDelete()
                }}
                className="p-2 text-surface-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                title="Delete"
             >
               <Trash2 className="w-5 h-5" />
             </button>
           )}
        </div>
      </div>

       {/* Decorative status bar on left */}
       <div className={`absolute left-0 top-0 bottom-0 w-1 ${config.barColor}`} />
    </div>
  )
}

function getStatusConfig(status: string) {
    const s = status.toLowerCase()
    if (['completed', 'done', 'success'].includes(s)) {
        return {
            icon: CheckCircle2,
            bgColor: 'bg-olive-100 dark:bg-olive-900/30',
            iconColor: 'text-olive-600 dark:text-olive-400',
            pillClass: 'bg-olive-100 dark:bg-olive-900/30 text-olive-700 dark:text-olive-300',
            barColor: 'bg-olive-500',
        }
    }
    if (['failed', 'error'].includes(s)) {
        return {
            icon: XCircle,
            bgColor: 'bg-red-100 dark:bg-red-900/30',
            iconColor: 'text-red-600 dark:text-red-400',
            pillClass: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300',
            barColor: 'bg-red-500',
        }
    }
    if (['processing', 'extracting', 'transcribing', 'detecting', 'translating', 'diarizing'].includes(s)) {
        return {
            icon: Loader2,
            bgColor: 'bg-olive-100 dark:bg-olive-900/30',
            iconColor: 'text-olive-600 dark:text-olive-400 animate-spin',
            pillClass: 'bg-olive-100 dark:bg-olive-900/30 text-olive-700 dark:text-olive-300',
            barColor: 'bg-olive-500',
        }
    }
    
    // Default / Queued
    return {
        icon: Clock,
        bgColor: 'bg-cream-200 dark:bg-dark-50',
        iconColor: 'text-surface-500',
        pillClass: 'bg-cream-200 dark:bg-dark-50 text-surface-600 dark:text-surface-400',
        barColor: 'bg-surface-300 dark:bg-surface-700',
    }
}

function formatStatus(status: string) {
    return status.charAt(0).toUpperCase() + status.slice(1).replace('_', ' ')
}
