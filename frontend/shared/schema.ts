import { sql } from "drizzle-orm";
import { pgTable, text, varchar, decimal, timestamp, integer, boolean, jsonb } from "drizzle-orm/pg-core";
import { createInsertSchema, createSelectSchema } from "drizzle-zod";
import { z } from "zod";

export const users = pgTable("users", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  username: text("username").notNull().unique(),
  email: text("email").notNull().unique(),
  full_name: text("full_name").notNull(),
  cpf: text("cpf").unique(),
  phone: text("phone"),
  password: text("password").notNull(),
  is_active: boolean("is_active").default(true),
  created_at: timestamp("created_at").defaultNow(),
});

export const events = pgTable("events", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  name: text("name").notNull(),
  description: text("description"),
  location: text("location").notNull(),
  city: text("city").notNull(),
  start: timestamp("start").notNull(),
  end: timestamp("end"),
  image: text("image"),
  is_active: boolean("is_active").default(true),
  created_at: timestamp("created_at").defaultNow(),
});

export const ticketClasses = pgTable("ticket_classes", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  event_id: varchar("event_id").notNull().references(() => events.id),
  name: text("name").notNull(),
  description: text("description"),
  price: decimal("price", { precision: 10, scale: 2 }).notNull(),
  ticket_type: text("ticket_type").notNull().default("normal"),
  available_quantity: integer("available_quantity"),
  created_at: timestamp("created_at").defaultNow(),
});

export const orders = pgTable("orders", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  user_id: varchar("user_id").references(() => users.id),
  total_amount: decimal("total_amount", { precision: 10, scale: 2 }).notNull(),
  status: text("status").notNull().default("pendente"),
  state: text("state").notNull().default("ativo"),
  payment_method: text("payment_method"),
  payment_id: text("payment_id"),
  payment_data: jsonb("payment_data"),
  paid_at: timestamp("paid_at"),
  redemption_token: text("redemption_token").unique(),
  created_at: timestamp("created_at").defaultNow(),
});

export const orderItems = pgTable("order_items", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  order_id: varchar("order_id").notNull().references(() => orders.id),
  event_id: varchar("event_id").notNull().references(() => events.id),
  ticket_class_id: varchar("ticket_class_id").notNull().references(() => ticketClasses.id),
  quantity: integer("quantity").notNull(),
  unit_price: decimal("unit_price", { precision: 10, scale: 2 }).notNull(),
  subtotal: decimal("subtotal", { precision: 10, scale: 2 }).notNull(),
  created_at: timestamp("created_at").defaultNow(),
});

export const tickets = pgTable("tickets", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  order_id: varchar("order_id").notNull().references(() => orders.id),
  order_item_id: varchar("order_item_id").notNull().references(() => orderItems.id),
  holder_name: text("holder_name"),
  holder_email: text("holder_email"),
  created_at: timestamp("created_at").defaultNow(),
});

// Insert schemas
export const insertUserSchema = createInsertSchema(users).omit({
  id: true,
  created_at: true,
});

export const insertEventSchema = createInsertSchema(events).omit({
  id: true,
  created_at: true,
});

export const insertOrderSchema = createInsertSchema(orders).omit({
  id: true,
  created_at: true,
  redemption_token: true,
});

export const insertTicketClassSchema = createInsertSchema(ticketClasses).omit({
  id: true,
  created_at: true,
});

export const insertOrderItemSchema = createInsertSchema(orderItems).omit({
  id: true,
  created_at: true,
});

export const insertTicketSchema = createInsertSchema(tickets).omit({
  id: true,
  created_at: true,
});

// Select schemas
export const selectUserSchema = createSelectSchema(users);
export const selectEventSchema = createSelectSchema(events);
export const selectOrderSchema = createSelectSchema(orders);
export const selectTicketClassSchema = createSelectSchema(ticketClasses);
export const selectOrderItemSchema = createSelectSchema(orderItems);
export const selectTicketSchema = createSelectSchema(tickets);

// Types
export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = z.infer<typeof selectUserSchema>;
export type InsertEvent = z.infer<typeof insertEventSchema>;
export type Event = z.infer<typeof selectEventSchema>;
export type InsertOrder = z.infer<typeof insertOrderSchema>;
export type Order = z.infer<typeof selectOrderSchema>;
export type InsertTicketClass = z.infer<typeof insertTicketClassSchema>;
export type TicketClass = z.infer<typeof selectTicketClassSchema>;
export type InsertOrderItem = z.infer<typeof insertOrderItemSchema>;
export type OrderItem = z.infer<typeof selectOrderItemSchema>;
export type InsertTicket = z.infer<typeof insertTicketSchema>;
export type Ticket = z.infer<typeof selectTicketSchema>;
