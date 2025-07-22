<?php

// --- 配置区 ---
define('IMAGE_BASE_DIR', 'api_ready_images');
$available_orientations = ['horizontal', 'vertical', 'square'];

/**
 * 发送一个JSON格式的错误响应
 * @param string $message 错误信息
 * @param int $code HTTP状态码
 */
function send_json_error($message, $code = 400) {
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['error' => $message]);
    exit;
}

// 1. 自动获取标签目录名
$tagDirs = array_diff(scandir(IMAGE_BASE_DIR), ['..', '.']);
if (empty($tagDirs)) {
    send_json_error('图片库目录未找到或为空。', 500);
}
$tagName = reset($tagDirs); // 使用第一个找到的标签目录

// 2. 获取并验证 orientation 参数
$orientation = $_GET['orientation'] ?? 'any';

if ($orientation !== 'any' && !in_array($orientation, $available_orientations)) {
    send_json_error('无效的 orientation 参数。可用值: ' . implode(', ', $available_orientations) . ', any');
}

// ==================================================================
// --- 核心逻辑修改开始 ---
// 根据 orientation 参数决定随机策略
// ==================================================================

$final_image_name = null;
$final_image_orientation = null;

if ($orientation === 'any') {
    // 新逻辑：从所有分类中随机选择
    $master_image_list = [];

    // 遍历所有可用的方向
    foreach ($available_orientations as $orient) {
        $manifest_path = implode(DIRECTORY_SEPARATOR, [IMAGE_BASE_DIR, $tagName, $orient, 'manifest.json']);
        
        if (file_exists($manifest_path)) {
            $image_list_json = file_get_contents($manifest_path);
            $image_list = json_decode($image_list_json, true);

            if (!empty($image_list)) {
                // 将图片文件名和其所属的分类一起存入主列表
                foreach ($image_list as $image_file) {
                    $master_image_list[] = [
                        'file' => $image_file,
                        'orientation' => $orient
                    ];
                }
            }
        }
    }

    if (empty($master_image_list)) {
        send_json_error("图片库中没有任何可用的图片。", 404);
    }

    // 从包含所有图片的主列表中随机选择一个
    $random_entry = $master_image_list[array_rand($master_image_list)];
    $final_image_name = $random_entry['file'];
    $final_image_orientation = $random_entry['orientation'];

} else {
    // 旧逻辑：处理特定分类的请求 (horizontal, vertical, square)
    $manifest_path = implode(DIRECTORY_SEPARATOR, [IMAGE_BASE_DIR, $tagName, $orientation, 'manifest.json']);

    if (!file_exists($manifest_path)) {
        send_json_error("指定的分类 '{$orientation}' 不存在或缺少 manifest.json 文件。", 404);
    }

    $image_list_json = file_get_contents($manifest_path);
    $image_list = json_decode($image_list_json, true);

    if (empty($image_list)) {
        send_json_error("指定的分类 '{$orientation}' 图片列表为空。", 404);
    }

    // 从指定分类的列表中随机选择一张
    $final_image_name = $image_list[array_rand($image_list)];
    $final_image_orientation = $orientation;
}

// --- 核心逻辑修改结束 ---


// 7. 构建图片在服务器上的文件路径并直接输出
$image_path = implode(DIRECTORY_SEPARATOR, [
    IMAGE_BASE_DIR,
    $tagName,
    $final_image_orientation, // 使用最终确定的图片方向
    $final_image_name      // 使用最终确定的图片文件名
]);

// 7.1 最终检查文件是否存在
if (!file_exists($image_path) || !is_readable($image_path)) {
    send_json_error("选中的图片文件 '{$final_image_name}' 在服务器上不存在或不可读。", 500);
}

// 7.2 获取图片的MIME类型
$mime_type = mime_content_type($image_path);
if ($mime_type === false) {
    $mime_type = 'application/octet-stream';
}

// 7.3 清除任何可能已经存在的输出缓冲
if (ob_get_level()) {
    ob_end_clean();
}

// 7.4 发送正确的HTTP头信息
header('Content-Type: ' . $mime_type);
header('Content-Length: ' . filesize($image_path));
header('Cache-Control: no-cache, no-store, must-revalidate');
header('Pragma: no-cache');
header('Expires: 0');

// 7.5 读取文件内容并直接输出到浏览器
readfile($image_path);
exit;