import type { Meta, StoryObj } from "@storybook/react";
import { Badge } from "./Badge";

const meta: Meta<typeof Badge> = {
  title: "UI/Badge",
  component: Badge,
  tags: ["autodocs"],
  argTypes: {
    variant: {
      control: "select",
      options: ["default", "secondary", "success", "warning", "destructive", "outline", "info"],
    },
    dot: { control: "boolean" },
    removable: { control: "boolean" },
  },
};

export default meta;
type Story = StoryObj<typeof Badge>;

export const Default: Story = {
  args: {
    variant: "default",
    children: "Default Badge",
  },
};

export const Success: Story = {
  args: {
    variant: "success",
    dot: true,
    children: "Success Badge",
  },
};

export const Warning: Story = {
  args: {
    variant: "warning",
    dot: true,
    children: "Warning Badge",
  },
};

export const Destructive: Story = {
  args: {
    variant: "destructive",
    children: "Destructive Badge",
  },
};
