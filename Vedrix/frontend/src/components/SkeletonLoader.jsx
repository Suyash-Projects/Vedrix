/**
 * SkeletonLoader — Animated loading placeholders for different layouts.
 *
 * Provides layout-matching skeleton loaders that maintain visual structure
 * while content loads. Uses shimmer animation for premium feel.
 *
 * Variants:
 * - DashboardSkeleton: Full dashboard with stat cards and table
 * - ReportSkeleton: Interview report with scores and charts
 * - TableSkeleton: Data table with header and rows
 * - ChartSkeleton: Chart/graph area placeholder
 * - CardSkeleton: Single card placeholder
 * - TextSkeleton: Text line placeholder
 *
 * Platform Completion Task 10.2
 */

const shimmerClass =
  'relative overflow-hidden before:absolute before:inset-0 before:-translate-x-full before:animate-[shimmer_2s_infinite] before:bg-gradient-to-r before:from-transparent before:via-white/5 before:to-transparent';

const chartBarHeights = Array.from({ length: 12 }, () => `${30 + Math.random() * 70}%`);

const Bone = ({ className = '', ...props }) => (
  <div
    className={`bg-white/5 rounded-xl ${shimmerClass} ${className}`}
    {...props}
  />
);

/* ── Dashboard Skeleton ────────────────────────────────────────────────────── */
export const DashboardSkeleton = () => (
  <div className="space-y-8 animate-pulse">
    {/* Header */}
    <div className="flex items-center justify-between">
      <div className="space-y-2">
        <Bone className="h-8 w-56 rounded-lg" />
        <Bone className="h-4 w-80 rounded-lg" />
      </div>
      <Bone className="h-10 w-32 rounded-xl" />
    </div>

    {/* Stat cards */}
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
      {[...Array(4)].map((_, i) => (
        <div
          key={i}
          className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6 space-y-4"
        >
          <Bone className="h-4 w-24 rounded-lg" />
          <Bone className="h-10 w-20 rounded-lg" />
          <Bone className="h-3 w-32 rounded-lg" />
        </div>
      ))}
    </div>

    {/* Table */}
    <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6 space-y-4">
      <Bone className="h-6 w-40 rounded-lg mb-6" />
      {[...Array(5)].map((_, i) => (
        <div key={i} className="flex items-center space-x-4 py-3">
          <Bone className="h-10 w-10 rounded-full" />
          <Bone className="h-4 w-40 rounded-lg" />
          <Bone className="h-4 w-24 rounded-lg" />
          <Bone className="h-4 w-20 rounded-lg ml-auto" />
        </div>
      ))}
    </div>
  </div>
);

/* ── Report Skeleton ───────────────────────────────────────────────────────── */
export const ReportSkeleton = () => (
  <div className="space-y-8 animate-pulse">
    {/* Header */}
    <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-8 space-y-4">
      <Bone className="h-8 w-64 rounded-lg" />
      <Bone className="h-4 w-96 rounded-lg" />
      <div className="flex space-x-4 mt-6">
        <Bone className="h-20 w-20 rounded-xl" />
        <Bone className="h-20 w-20 rounded-xl" />
        <Bone className="h-20 w-20 rounded-xl" />
      </div>
    </div>

    {/* Radar chart placeholder */}
    <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-8">
      <Bone className="h-6 w-32 rounded-lg mb-6" />
      <div className="flex items-center justify-center">
        <Bone className="h-64 w-64 rounded-full" />
      </div>
    </div>

    {/* Question breakdown */}
    <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-8 space-y-4">
      <Bone className="h-6 w-48 rounded-lg mb-4" />
      {[...Array(4)].map((_, i) => (
        <div key={i} className="border border-white/5 rounded-xl p-5 space-y-3">
          <Bone className="h-5 w-full rounded-lg" />
          <Bone className="h-3 w-3/4 rounded-lg" />
          <div className="flex items-center space-x-4 mt-3">
            <Bone className="h-8 w-16 rounded-lg" />
            <Bone className="h-2 flex-1 rounded-full" />
          </div>
        </div>
      ))}
    </div>
  </div>
);

/* ── Table Skeleton ────────────────────────────────────────────────────────── */
export const TableSkeleton = ({ rows = 5, cols = 4 }) => (
  <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6 space-y-4 animate-pulse">
    {/* Header row */}
    <div className="flex items-center space-x-4 pb-4 border-b border-white/5">
      {[...Array(cols)].map((_, i) => (
        <Bone key={i} className={`h-4 rounded-lg ${i === 0 ? 'w-40' : 'w-24'}`} />
      ))}
    </div>
    {/* Data rows */}
    {[...Array(rows)].map((_, i) => (
      <div key={i} className="flex items-center space-x-4 py-3">
        {[...Array(cols)].map((_, j) => (
          <Bone key={j} className={`h-4 rounded-lg ${j === 0 ? 'w-40' : 'w-24'}`} />
        ))}
      </div>
    ))}
  </div>
);

/* ── Chart Skeleton ────────────────────────────────────────────────────────── */
export const ChartSkeleton = ({ height = 'h-64' }) => (
  <div className={`bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6 animate-pulse`}>
    <Bone className="h-6 w-40 rounded-lg mb-6" />
    <div className={`${height} flex items-end space-x-2`}>
      {[...Array(12)].map((_, i) => (
        <Bone
          key={i}
          className="flex-1 rounded-t-lg"
          style={{ height: chartBarHeights[i] }}
        />
      ))}
    </div>
  </div>
);

/* ── Card Skeleton ─────────────────────────────────────────────────────────── */
export const CardSkeleton = () => (
  <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6 space-y-4 animate-pulse">
    <Bone className="h-5 w-36 rounded-lg" />
    <Bone className="h-4 w-full rounded-lg" />
    <Bone className="h-4 w-3/4 rounded-lg" />
    <Bone className="h-10 w-28 rounded-xl mt-4" />
  </div>
);

/* ── Text Skeleton ─────────────────────────────────────────────────────────── */
export const TextSkeleton = ({ lines = 3, className = '' }) => (
  <div className={`space-y-3 animate-pulse ${className}`}>
    {[...Array(lines)].map((_, i) => (
      <Bone
        key={i}
        className={`h-4 rounded-lg ${i === lines - 1 ? 'w-2/3' : 'w-full'}`}
      />
    ))}
  </div>
);

/* ── Profile Skeleton ──────────────────────────────────────────────────────── */
export const ProfileSkeleton = () => (
  <div className="space-y-6 animate-pulse">
    <div className="flex items-center space-x-6">
      <Bone className="h-24 w-24 rounded-full" />
      <div className="space-y-3">
        <Bone className="h-7 w-48 rounded-lg" />
        <Bone className="h-4 w-32 rounded-lg" />
        <Bone className="h-3 w-56 rounded-lg" />
      </div>
    </div>
    <div className="grid grid-cols-3 gap-4">
      {[...Array(3)].map((_, i) => (
        <div key={i} className="bg-white/5 border border-white/10 rounded-xl p-4 space-y-3">
          <Bone className="h-4 w-20 rounded-lg" />
          <Bone className="h-8 w-16 rounded-lg" />
        </div>
      ))}
    </div>
  </div>
);

/* ── Default export (DashboardSkeleton) ────────────────────────────────────── */
const SkeletonLoader = DashboardSkeleton;
export default SkeletonLoader;
