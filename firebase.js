// firebase.js
import { initializeApp } from "https://www.gstatic.com/firebasejs/9.22.2/firebase-app.js";
import { getDatabase, ref, set, push, onValue, update, get, child } from "https://www.gstatic.com/firebasejs/9.22.2/firebase-database.js";

const firebaseConfig = {
  apiKey: "AIzaSyDE2i4hR0bDpen6MTuvKz0cs3PzU8DfqQw",
  authDomain: "markapp-23e6b.firebaseapp.com",
  databaseURL: "https://markapp-23e6b-default-rtdb.asia-southeast1.firebasedatabase.app",
  projectId: "markapp-23e6b",
  storageBucket: "markapp-23e6b.firebasestorage.app",
  messagingSenderId: "693861021165",
  appId: "1:693861021165:web:c144f2dc67c9d79068e3e4",
  measurementId: "G-RQLSXLRFNZ"
};

const app = initializeApp(firebaseConfig);
const db = getDatabase(app);

export { db, ref, set, push, onValue, update, get, child };
