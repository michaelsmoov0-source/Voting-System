import React from "react";
import { cn } from "../utils";

const Loader = ({ 
  size = "md", 
  variant = "default", 
  text = "Loading...", 
  showText = true,
  className = "",
  textClassName = "",
  ...props 
}) => {
  const sizeClasses = {
    sm: "w-4 h-4",
    md: "w-6 h-6", 
    lg: "w-8 h-8",
    xl: "w-12 h-12",
  };

  const textSizes = {
    sm: "text-xs",
    md: "text-sm", 
    lg: "text-base",
    xl: "text-lg",
  };

  const variantClasses = {
    default: "border-brand-600",
    primary: "border-blue-600",
    secondary: "border-gray-600",
    success: "border-green-600",
    warning: "border-yellow-600",
    error: "border-red-600",
    white: "border-white",
  };

  return (
    <div 
      className={cn("flex items-center justify-center gap-2", className)}
      {...props}
    >
      <div 
        className={cn(
          "animate-spin rounded-full border-2 border-t-transparent",
          sizeClasses[size],
          variantClasses[variant]
        )}
      />
      {showText && (
        <span className={cn("text-slate-600", textSizes[size], textClassName)}>
          {text}
        </span>
      )}
    </div>
  );
};

export default Loader;
