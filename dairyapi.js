const express = require('express');
const { Sequelize, DataTypes } = require('sequelize');
const cors = require('cors');

const app = express();
app.use(express.json());
app.use(cors());

const sequelize = new Sequelize("dairy", "root", "mysql123", {
    host: "localhost",
    dialect: "mysql",
});

const User = sequelize.define("users", {
    uid: {
        type: DataTypes.INTEGER,
        autoIncrement: true,
        primaryKey: true
    },
    username: { type: DataTypes.STRING, allowNull: false, unique: true },
    password: { type: DataTypes.STRING, allowNull: false },
    createdAt: { type: DataTypes.DATE, defaultValue: Sequelize.NOW }
});

const Dairy = sequelize.define("dairy", {
    dairy_id: {
        type: DataTypes.INTEGER,
        autoIncrement: true,
        primaryKey: true
    },
    user_id: {
        type: DataTypes.INTEGER,
        allowNull: false,
        references: {
            model: User,
            key: "uid"
        }
    },
    name: { type: DataTypes.STRING, allowNull: false },
    description: { type: DataTypes.STRING },
    date: { type: DataTypes.DATE, defaultValue: Sequelize.NOW },
    image: { type: DataTypes.STRING },
    location: { type: DataTypes.STRING }
});

sequelize.sync({ alter: true }).then(() => {
    console.log("Database & tables created!");
});

app.post("/signup", async (req, res) => {
    try {
        const { name, password } = req.body;
        const userExists = await User.findOne({ where: { username: name } });
        if (userExists) {
            return res.status(400).json({ message: "User already exists" });
        }
        await User.create({ username: name, password });
        res.status(201).json({ message: "User successfully created" });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post("/login", async (req, res) => {
    try {
        const { email, password } = req.body;
        const user = await User.findOne({ where: { username: email, password } });
        if (!user) {
            return res.status(400).json({ message: "Invalid username or password" });
        }
        res.status(200).json({ message: "Login successful" });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post("/dairy", async (req, res) => {
    try {
        const { user_id, name, description, date, image, location } = req.body;
        await Dairy.create({ user_id, name, description, date, image, location });
        res.status(201).json({ message: "Dairy successfully created" });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get("/get_dairy/:id", async (req, res) => {
    try {
        const { id } = req.params;
        const dairies = await Dairy.findAll({ where: { user_id: id } });
        if (dairies.length === 0) {
            return res.status(404).json({ message: "No dairy entries found" });
        }
        res.status(200).json(dairies);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.delete("/dairy/:id", async (req, res) => {
    try {
        const { id } = req.params;
        const deleted = await Dairy.destroy({ where: { dairy_id: id } });
        if (!deleted) {
            return res.status(404).json({ message: "Dairy entry not found" });
        }
        res.status(200).json({ message: "Dairy successfully deleted" });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.put("/dairy/:id", async (req, res) => {
    try {
        const { id } = req.params;
        const { name, description, date, image, location } = req.body;
        const updated = await Dairy.update(
            { name, description, date, image, location },
            { where: { dairy_id: id } }
        );
        if (updated[0] === 0) {
            return res.status(404).json({ message: "Dairy entry not found" });
        }
        res.status(200).json({ message: "Dairy successfully updated" });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.listen(3000, () => {
    console.log("Server is running on port 3000");
});
