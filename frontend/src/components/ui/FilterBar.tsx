import React from "react";
import { SearchBox } from "./SearchBox";
import { Chip } from "./Chip";
import { Select } from "./Select";

export interface FilterBarProps {
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
  categories?: string[];
  selectedCategory?: string;
  onCategorySelect?: (cat: string) => void;
  sortOptions?: Array<{ label: string; value: string }>;
  selectedSort?: string;
  onSortChange?: (sort: string) => void;
  actions?: React.ReactNode;
  className?: string;
}

export const FilterBar: React.FC<FilterBarProps> = ({
  searchQuery = "",
  onSearchChange,
  categories = [],
  selectedCategory,
  onCategorySelect,
  sortOptions = [],
  selectedSort,
  onSortChange,
  actions,
  className = "",
}) => {
  return (
    <div className={`bg-card border rounded-2xl p-4 shadow-sm flex flex-col md:flex-row md:items-center gap-4 justify-between ${className}`}>
      <div className="flex flex-1 flex-col sm:flex-row gap-3">
        {onSearchChange && (
          <div className="w-full sm:max-w-xs">
            <SearchBox
              placeholder="Search items..."
              value={searchQuery}
              onSearch={onSearchChange}
            />
          </div>
        )}

        {categories.length > 0 && onCategorySelect && (
          <div className="flex flex-wrap gap-2 items-center">
            {categories.map((cat) => (
              <Chip
                key={cat}
                variant="interactive"
                selected={selectedCategory === cat}
                onSelect={() => onCategorySelect(cat)}
              >
                {cat}
              </Chip>
            ))}
          </div>
        )}
      </div>

      <div className="flex items-center gap-3">
        {sortOptions.length > 0 && onSortChange && (
          <Select
            options={sortOptions}
            value={selectedSort || sortOptions[0]?.value}
            onChange={(e) => onSortChange(e.target.value)}
            className="w-40"
          />
        )}
        {actions}
      </div>
    </div>
  );
};
