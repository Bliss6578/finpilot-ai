import { createContext, type ReactNode, useContext, useEffect, useState } from "react";

export type DateRangeDays = 7 | 30 | 90;

type DateRangeContextValue = {
  days: DateRangeDays;
  setDays: (days: DateRangeDays) => void;
};

const STORAGE_KEY = "paymentor_date_range";
const DateRangeContext = createContext<DateRangeContextValue | null>(null);

function initialDays(): DateRangeDays {
  const saved = Number(window.localStorage.getItem(STORAGE_KEY));
  return saved === 7 || saved === 90 ? saved : 30;
}

export function DateRangeProvider({ children }: { children: ReactNode }) {
  const [days, setDays] = useState<DateRangeDays>(initialDays);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, String(days));
  }, [days]);

  return (
    <DateRangeContext.Provider value={{ days, setDays }}>
      {children}
    </DateRangeContext.Provider>
  );
}

export function useDateRange() {
  const context = useContext(DateRangeContext);
  if (!context) throw new Error("useDateRange must be used inside DateRangeProvider");
  return context;
}
