/**
 * Endgame OS v2 - M3 Slider Component
 * A clean, minimalist slider for energy calibration
 */
import * as React from 'react';
import clsx from 'clsx';

interface SliderProps {
  value: number[];
  onValueChange: (value: number[]) => void;
  max?: number;
  min?: number;
  step?: number;
  className?: string;
}

export default function Slider({
  value,
  onValueChange,
  max = 100,
  min = 0,
  step = 1,
  className
}: SliderProps) {
  const percent = ((value[0] - min) / (max - min)) * 100;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onValueChange([parseInt(e.target.value, 10)]);
  };

  return (
    <div className={clsx("relative w-full flex items-center group touch-none select-none h-5", className)}>
      {/* Track */}
      <div className="relative h-1 w-full grow overflow-hidden rounded-full bg-[var(--md-sys-color-surface-variant)]">
        <div 
          className="absolute h-full bg-[var(--md-sys-color-primary)] transition-all duration-300" 
          style={{ width: `${percent}%` }} 
        />
      </div>
      
      {/* Input Overlay (Invisible but functional) */}
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value[0]}
        onChange={handleChange}
        className="absolute w-full h-full opacity-0 cursor-pointer z-20"
      />
      
      {/* Thumb (Visual only, follows input) */}
      <div 
        className="absolute h-5 w-5 rounded-full border-2 border-[var(--md-sys-color-primary)] bg-[var(--md-sys-color-surface)] shadow-sm transition-all duration-200 group-hover:scale-110 group-active:scale-95 z-10 pointer-events-none"
        style={{ left: `calc(${percent}% - 10px)` }}
      />
    </div>
  );
}
