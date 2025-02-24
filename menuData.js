export let menuItems = [];

async function loadMenu() {
    try {
        const response = await fetch("menuData.json");
        menuItems = await response.json();
        console.log("✅ 菜單載入成功", menuItems);
    } catch (error) {
        console.error("❌ 無法讀取菜單", error);
    }
}

document.addEventListener("DOMContentLoaded", async () => {
  await loadMenu();
  console.log("✅ 菜單載入完成，可用於 AI 建議");
});
