-- ============================================================
-- FOOD DELIVERY MANAGEMENT SYSTEM — SEED DATA
-- Run AFTER schema.sql
-- NOTE: Password hashes below are for demo ONLY.
--       Run setup_db.py for proper Werkzeug-hashed passwords.
-- ============================================================

USE food_delivery;

-- ─── Categories ─────────────────────────────────────────────
INSERT IGNORE INTO categories (name, description) VALUES
('Pizza',        'Classic Italian pizzas with fresh toppings'),
('Burger',       'Juicy burgers and sandwiches'),
('Biryani',      'Aromatic rice dishes with spices'),
('Chinese',      'Noodles, fried rice and Asian delights'),
('South Indian', 'Dosas, idlis, vadas and more'),
('Desserts',     'Sweets, cakes and frozen treats'),
('Beverages',    'Cold drinks, juices and shakes'),
('Sandwich',     'Fresh and filling sandwiches');

-- ─── Restaurants (passwords set by setup_db.py) ─────────────
-- Dummy hash placeholder — DO NOT USE IN PRODUCTION
-- Replace with real hashes via setup_db.py
INSERT IGNORE INTO restaurants
    (name, email, password_hash, phone, address, cuisine_type, description, delivery_fee, rating)
VALUES
('Pizza Palace',
 'pizza@palace.com',
 'REPLACE_WITH_HASH',
 '9876543210',
 '12 MG Road, Bangalore',
 'Italian',
 'Authentic wood-fired pizzas baked to perfection. Family recipes since 1990.',
 30.00, 4.5),

('Burger Barn',
 'burger@barn.com',
 'REPLACE_WITH_HASH',
 '9876543211',
 '45 Brigade Road, Bangalore',
 'American',
 'Gourmet burgers, crispy fries and thick milkshakes.',
 25.00, 4.2),

('Spice Garden',
 'spice@garden.com',
 'REPLACE_WITH_HASH',
 '9876543212',
 '78 Jayanagar 4th Block, Bangalore',
 'Indian',
 'Authentic South Indian and Biryani cuisine prepared with love.',
 20.00, 4.7),

('Dragon Palace',
 'dragon@palace.com',
 'REPLACE_WITH_HASH',
 '9876543213',
 '23 Indiranagar, Bangalore',
 'Chinese',
 'The best Chinese food in town – noodles, dim sum and more.',
 35.00, 4.3),

('Sweet Dreams',
 'sweet@dreams.com',
 'REPLACE_WITH_HASH',
 '9876543214',
 '56 Koramangala, Bangalore',
 'Desserts',
 'Heavenly desserts, cakes and ice cream for every occasion.',
 15.00, 4.6);

-- NOTE: After running setup_db.py, you can comment out the rows above
--       as setup_db.py inserts them with real hashed passwords.
