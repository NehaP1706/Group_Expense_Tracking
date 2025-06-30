// server.js
const express = require('express');
const bodyParser = require('body-parser');
const mongoose = require('mongoose');
const { v4: uuidv4 } = require('uuid');
require('dotenv').config();

const multer = require('multer');
const path = require('path');
const fs = require('fs');

const app = express();
app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.json());
app.use(express.static('public'));

mongoose.connect(process.env.MONGO_URI, {
  useNewUrlParser: true,
  useUnifiedTopology: true,
}).then(() => {
  console.log('✅ Connected to MongoDB Atlas');
}).catch((err) => {
  console.error('❌ MongoDB connection error:', err);
});

const userSchema = new mongoose.Schema({
  userId: String,
  firstName: String,
  lastName: String,
  mobile: String,
  currency: String,
  password: String,
  friends: [String],
  groups: [String],
  history: [{
    amount: Number,
    type: String,
    description: String,
    timestamp: Date
  }],
  debt: {
    type: Number,
    default: 0
  }
});

const groupSchema = new mongoose.Schema({
  groupId: String,
  groupName: String,
  createdBy: String,
  members: [String],
  events: [{
    eventName: String,
    description: String,
    duration: String,
    createdAt: Date,
    transactions: [{
      owedBy: String,
      owedTo: String,
      reason: String,
      amount: Number,
      timestamp: Date,
      isPaid: Boolean
    }]
  }]
});

const User = mongoose.model('User', userSchema);
const Group = mongoose.model('Group', groupSchema);

app.get('/signup', (req, res) => {
  res.sendFile(__dirname + '/public/signup.html');
});

app.get('/login', (req, res) => {
  res.sendFile(__dirname + '/public/login.html');
});

app.post('/signup', async (req, res) => {
  const user = new User({
    userId: uuidv4(),
    firstName: req.body.firstName,
    lastName: req.body.lastName,
    mobile: req.body.mobile,
    currency: req.body.currency,
    password: req.body.password,
    friends: [],
    groups: [],
    history: [],
  });

  await user.save();
  res.send("✅ User registered successfully! ID: " + user.userId);
});

app.post('/login', async (req, res) => {
  const { firstName, password } = req.body;
  try {
    const user = await User.findOne({ firstName });
    if (!user || user.password !== password) {
      return res.send("❌ Invalid user or password.");
    }
    res.redirect(`/dashboard.html?userId=${user.userId}`);
  } catch (err) {
    console.error(err);
    res.status(500).send("Server error.");
  }
});

app.get('/api/profile', async (req, res) => {
  const { userId } = req.query;

  try {
    const user = await User.findOne({ userId });

    if (!user) {
      return res.status(404).json({ error: "User not found" }); // ✅ JSON response
    }

    res.json(user); // valid user found
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Server error" }); // ✅ JSON response
  }
});

app.get('/api/group/:groupId', async (req, res) => {
  const { groupId } = req.params;
  try {
    const group = await Group.findOne({ groupId });
    if (!group) return res.status(404).send("Group not found");
    res.json(group);
  } catch (err) {
    res.status(500).send("Server error");
  }
});

app.get('/api/groupsForUser', async (req, res) => {
  const { userId } = req.query;
  if (!userId) return res.status(400).send("Missing userId");
  try {
    const groups = await Group.find({
      $or: [
        { createdBy: userId },
        { members: userId }
      ]
    });
    res.json(groups);
  } catch (err) {
    console.error("❌ Error fetching groups for user:", err);
    res.status(500).send("Server error");
  }
});

app.post('/api/groups', async (req, res) => {
  const { createdBy, groupName, duration, members, events } = req.body;
  if (!createdBy || !groupName || !members || !Array.isArray(members)) {
    return res.status(400).send("Missing required fields");
  }
  try {
    const groupId = uuidv4();
    const newGroup = new Group({
      groupId,
      groupName,
      createdBy,
      duration,
      members,
      events: events.map(event => ({ ...event, createdAt: new Date() }))
    });
    await newGroup.save();
    await User.updateMany(
      { userId: { $in: members } },
      { $push: { groups: groupId } }
    );
    for (const event of events) {
      for (const tx of event.transactions) {
        const { owedBy, amount } = tx;
        if (!owedBy || !amount) continue;
        await User.updateOne(
          { userId: owedBy },
          { $inc: { debt: amount } }
        );
      }
    }
    res.status(201).send({ message: "✅ Group created", groupId });
  } catch (err) {
    console.error("Error creating group:", err);
    res.status(500).send("Server error");
  }
});

app.post('/api/groups/:groupId/addEvent', async (req, res) => {
  const groupId = req.params.groupId;
  const event = req.body.event;
  try {
    const group = await Group.findOne({ groupId });
    if (!group) {
      return res.status(404).json({ error: "Group not found" });
    }
    if (!event.createdAt) {
      event.createdAt = new Date();
    }
    group.events.push(event);
    await group.save();
    for (const tx of event.transactions || []) {
      const { owedBy, amount } = tx;
      if (!owedBy || !amount) continue;
      await User.updateOne(
        { userId: owedBy },
        { $inc: { debt: amount } }
      );
    }
    res.status(200).json({ success: true });
  } catch (err) {
    console.error("Error while adding event:", err);
    res.status(500).json({ error: "Server error" });
  }
});

app.get("/api/transactions", async (req, res) => {
  const { userId } = req.query;
  const allGroups = await Group.find({
    "events.transactions": {
      $elemMatch: {
        $or: [{ owedBy: userId }, { owedTo: userId }],
        isPaid: true
      }
    }
  });

  const result = [];
  allGroups.forEach(group => {
    group.events.forEach(event => {
      event.transactions.forEach(txn => {
        if (txn.isPaid && (txn.owedBy === userId || txn.owedTo === userId)) {
          result.push({
            amount: txn.amount,
            owedBy: txn.owedBy,
            owedTo: txn.owedTo,
            reason: txn.reason,
            currency: group.currency || "INR",
            paymentTimestamp: txn.timestamp
          });
        }
      });
    });
  });

  res.json(result);
});

const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    const dir = './uploads';
    if (!fs.existsSync(dir)) fs.mkdirSync(dir);
    cb(null, dir);
  },
  filename: function (req, file, cb) {
    const timestamp = Date.now();
    const ext = path.extname(file.originalname);
    cb(null, `receipt_${timestamp}${ext}`);
  }
});

const upload = multer({ storage });

app.post('/api/uploadReceiptOnly', upload.single('receipt'), async (req, res) => {
  const { groupId, eventName, timestamp, owedBy, owedTo } = req.body;
  const receiptPath = req.file ? req.file.filename : null;

  if (!receiptPath || !groupId || !eventName || !timestamp || !owedBy || !owedTo) {
    return res.status(400).json({ error: "Missing required fields or file" });
  }

  try {
    const group = await Group.findOne({ groupId });
    if (!group) return res.status(404).json({ error: "Group not found" });

    let updated = false;

    for (const event of group.events) {
      if (event.eventName === eventName) {
        for (const txn of event.transactions) {
          if (
            txn.timestamp?.toISOString() === timestamp &&
            txn.owedBy === owedBy &&
            txn.owedTo === owedTo
          ) {
            txn.receipt = `/uploads/${receiptPath}`;  // Save relative path
            updated = true;
            break;
          }
        }
        if (updated) break;
      }
    }

    if (!updated) {
      return res.status(404).json({ error: "Transaction not found" });
    }

    await group.save();
    res.json({ message: "✅ Receipt uploaded and saved." });
  } catch (err) {
    console.error("UploadReceiptOnly Error:", err);
    res.status(500).json({ error: "Server error while uploading receipt." });
  }
});

app.post('/api/markTransactionPaid', async (req, res) => {
  const { groupId, eventName, timestamp, owedBy, owedTo } = req.body;

  if (!groupId || !eventName || !timestamp || !owedBy || !owedTo) {
    return res.status(400).json({ error: "Missing required fields" });
  }

  try {
    const group = await Group.findOne({ groupId });
    if (!group) return res.status(404).json({ error: "Group not found" });

    let updated = false;

    for (const event of group.events) {
      if (event.eventName === eventName) {
        for (const txn of event.transactions) {
          if (
            txn.timestamp?.toISOString() === timestamp &&
            txn.owedBy === owedBy &&
            txn.owedTo === owedTo &&
            !txn.isPaid
          ) {
            txn.isPaid = true;
            await User.updateOne(
              { userId: owedBy },
              { $inc: { debt: -txn.amount } }
            );
            updated = true;
            break;
          }
        }
        if (updated) break;
      }
    }

    if (!updated) {
      return res.status(404).json({ error: "Transaction not found or already paid" });
    }

    await group.save();
    res.status(200).json({ message: "✅ Transaction marked as paid and debt updated" });
  } catch (err) {
    console.error("Error updating transaction:", err);
    res.status(500).json({ error: "Server error" });
  }
});

app.post('/api/groups/:groupId/updateMembers', async (req, res) => {
  const { groupId } = req.params;
  const { members} = req.body; // ✅ Fix here

  console.log("Incoming members update:", {
    body: req.body,
    params: req.params,
    query: req.query 
    });

  if (!Array.isArray(members)) {
    return res.status(400).json({ error: "Missing userId or members array" });
  }

  try {
    const group = await Group.findOne({ groupId });

    if (!group) {
      return res.status(404).json({ error: "Group not found" });
    }

    group.members = members;
    await group.save();

    res.json({ message: "Group members updated successfully" });
  } catch (err) {
    console.error("Error updating group members:", err);
    res.status(500).json({ error: "Internal server error" });
  }
});

app.listen(3000, () => {
  console.log('🚀 Server running at http://localhost:3000');
});
