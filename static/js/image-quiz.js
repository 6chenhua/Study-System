// 图片选择题交互逻辑
document.addEventListener('DOMContentLoaded', function() {
    initializeImageChoiceQuestions();

    function initializeImageChoiceQuestions() {
        const imageChoiceContainers = document.querySelectorAll('.image-choice-container');
        
        imageChoiceContainers.forEach(container => {
            const imageOptions = container.querySelectorAll('.image-option');
            const radioInputs = container.querySelectorAll('.image-choice-input');
            // let isAnswered = false; // 不再需要此变量，因为允许重复选择

            // 不再创建"下一题"按钮
            // const nextButton = document.createElement('button');
            // nextButton.className = 'next-question-btn';
            // nextButton.textContent = '下一题';
            // nextButton.type = 'button';
            // container.appendChild(nextButton);
            
            radioInputs.forEach(input => {
                input.addEventListener('change', function() {
                    // if (isAnswered) return; // 允许重复选择，移除此行
                    // isAnswered = true; // 允许重复选择，移除此行
                    
                    // 移除所有视觉反馈相关的类
                    imageOptions.forEach(opt => {
                        opt.classList.remove('selected-correct', 'selected-incorrect');
                    });

                    // 为当前选中的选项添加一个通用选中样式（如果需要）
                    // const selectedOption = this.closest('.image-option');
                    // selectedOption.classList.add('selected-generic'); // 可以定义一个新的 'selected-generic' 样式

                    // 允许再次选择，不禁用其他选项
                    // imageOptions.forEach(option => {
                    //     const radio = option.querySelector('.image-choice-input');
                    //     radio.disabled = false; // 确保所有选项都可选
                    // });

                    // 不再显示"下一题"按钮
                    // nextButton.classList.add('visible');
                });
            });
            
            imageOptions.forEach(option => {
                option.addEventListener('click', function(e) {
                    // if (isAnswered) return; // 允许重复选择
                    
                    const input = this.querySelector('.image-choice-input');
                    if (input && !e.target.classList.contains('image-choice-input')) {
                        // 如果点击的不是radio本身，则选中它并触发change
                        if (!input.checked) {
                            input.checked = true;
                            const event = new Event('change', { bubbles: true });
                            input.dispatchEvent(event);
                        }
                    }
                });
            });
            
            // 不再需要"下一题"按钮的事件监听器
            // nextButton.addEventListener('click', function() {
            //     const submitButton = document.querySelector('button[type="submit"]');
            //     if (submitButton) {
            //         submitButton.click();
            //     }
            // });
        });
    }
}); 