import type { ReactNode } from "react";

import { cx } from "./utils";

export interface TableColumn<T> {
  key: string;
  label: string;
  className?: string;
  render: (row: T) => ReactNode;
}

interface DataTableProps<T> {
  columns: Array<TableColumn<T>>;
  emptyLabel: string;
  rows: T[];
}

export function DataTable<T>({ columns, emptyLabel, rows }: DataTableProps<T>) {
  return (
    <div className="overflow-hidden rounded-card border border-tec-border/20">
      <table className="w-full border-collapse text-left text-sm">
        <thead className="bg-white/[0.035] text-xs uppercase text-tec-muted">
          <tr>
            {columns.map((column) => (
              <th className={cx("px-4 py-3 font-semibold", column.className)} key={column.key}>
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length ? (
            rows.map((row, index) => (
              <tr className="border-t tp-row-border hover:bg-white/[0.025]" key={index}>
                {columns.map((column) => (
                  <td className={cx("px-4 py-3 align-middle text-tec-subtle", column.className)} key={column.key}>
                    {column.render(row)}
                  </td>
                ))}
              </tr>
            ))
          ) : (
            <tr>
              <td className="px-4 py-8 text-center text-tec-muted" colSpan={columns.length}>
                {emptyLabel}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
