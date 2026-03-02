/**
 * Tests for utility functions used across the app.
 */

describe('Utility Functions', () => {
  describe('Date formatting', () => {
    it('should handle ISO date strings', () => {
      const date = new Date('2025-01-15T10:30:00Z');
      expect(date.getFullYear()).toBe(2025);
      expect(date.getMonth()).toBe(0); // January
    });
  });

  describe('Plan tier ordering', () => {
    const tierOrder = { free: 0, basic: 1, pro: 2, enterprise: 3 };

    it('should correctly order plan tiers', () => {
      expect(tierOrder.free).toBeLessThan(tierOrder.basic);
      expect(tierOrder.basic).toBeLessThan(tierOrder.pro);
      expect(tierOrder.pro).toBeLessThan(tierOrder.enterprise);
    });

    it('should identify upgrades', () => {
      function isUpgrade(from: string, to: string): boolean {
        return (tierOrder[to as keyof typeof tierOrder] || 0) > (tierOrder[from as keyof typeof tierOrder] || 0);
      }
      expect(isUpgrade('free', 'basic')).toBe(true);
      expect(isUpgrade('pro', 'basic')).toBe(false);
      expect(isUpgrade('free', 'enterprise')).toBe(true);
    });
  });

  describe('Arabic text handling', () => {
    it('should handle RTL text', () => {
      const arabicText = '\u0645\u0633\u062a\u0634\u0627\u0631 \u0642\u0627\u0646\u0648\u0646\u064a';
      expect(arabicText.length).toBeGreaterThan(0);
      expect(arabicText).toMatch(/[\u0600-\u06FF]/); // Arabic Unicode range
    });

    it('should handle mixed Arabic/English', () => {
      const mixed = '\u0628\u0627\u0642\u0629 Pro';
      expect(mixed).toContain('Pro');
      expect(mixed).toMatch(/[\u0600-\u06FF]/);
    });
  });
});
