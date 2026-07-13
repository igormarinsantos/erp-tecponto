import type { HTMLAttributes, ReactNode } from "react";

import { cx } from "./utils";

type RowProps = HTMLAttributes<HTMLTableRowElement> & Record<`data-${string}`, string | number | undefined>;

export interface TableColumn<T> {
  key: string;
  label: string;
  className?: string;
  render: (row: T) => ReactNode;
}

interface DataTableProps<T> {
  columns: Array<TableColumn<T>>;
  emptyLabel: string;
  getRowProps?: (row: T) => RowProps;
  onRowClick?: (row: T) => void;
  rows: T[];
  tableMinWidthClassName?: string;
}

export function DataTable<T>({ columns, emptyLabel, getRowProps, onRowClick, rows, tableMinWidthClassName = "min-w-[1100px]" }: DataTableProps<T>) {
  return (
    <div className="overflow-x-auto rounded-card border border-tec-border/15">
      <table className={cx("tp-data-table w-full table-fixed border-collapse text-left text-sm", tableMinWidthClassName)}>
        <thead className="bg-tec-field/55 text-xs uppercase text-tec-muted">
          <tr>
            {columns.map((column) => (
              <th className={cx("px-4 py-3 font-bold", column.className)} key={column.key}>
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length ? (
            rows.map((row, index) => {
              const rowProps = getRowProps?.(row) ?? {};
              return (
                <tr
                  {...rowProps}
                  className={cx(
                    "border-t border-tec-border/10 transition",
                    onRowClick ? "cursor-pointer hover:bg-tec-field/55" : "",
                    rowProps.className,
                  )}
                  key={index}
                  onClick={onRowClick ? () => onRowClick(row) : rowProps.onClick}
                  onKeyDown={
                    onRowClick
                      ? (event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            onRowClick(row);
                          }
                        }
                      : rowProps.onKeyDown
                  }
                  role={onRowClick ? "button" : rowProps.role}
                  tabIndex={onRowClick ? 0 : rowProps.tabIndex}
                >
                  {columns.map((column) => (
                    <td className={cx("px-4 py-2.5 align-middle text-tec-subtle", column.className)} key={column.key}>
                      {column.render(row)}
                    </td>
                  ))}
                </tr>
              );
            })
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
